import json
import logging
import subprocess
import time
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')).rstrip('/')

    def get_installed_models_cli(self):
        """Fetch models using the `ollama list` CLI command."""
        models = []
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                # Line 0 is header: NAME ID SIZE MODIFIED
                for line in lines[1:]:
                    parts = line.split()
                    if parts:
                        model_name = parts[0].strip()
                        if model_name and model_name not in models:
                            models.append(model_name)
        except Exception as e:
            logger.debug(f"CLI 'ollama list' failed: {e}")
        return models

    def get_installed_models_api(self):
        """Fetch models using Ollama HTTP API /api/tags."""
        models = []
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('models', []):
                    name = item.get('name') or item.get('model')
                    if name and name not in models:
                        models.append(name)
        except Exception as e:
            logger.debug(f"HTTP '/api/tags' failed: {e}")
        return models

    def get_installed_models(self):
        """
        Dynamically discover installed models on this air-gapped machine.
        Tries CLI 'ollama list' first, then falls back to or merges with HTTP API /api/tags.
        """
        cli_models = self.get_installed_models_cli()
        api_models = self.get_installed_models_api()

        # Merge unique keeping order
        combined = []
        for m in cli_models + api_models:
            if m not in combined:
                combined.append(m)
        return combined

    def check_health(self):
        """Verify if Ollama service is reachable and responsive."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def stream_chat(self, model, messages, system_prompt=None, temperature=0.7):
        """
        Streams chat responses from Ollama /api/chat.
        Yields dicts with content chunks, and the final chunk includes timing and bottleneck metrics.
        """
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({'role': 'system', 'content': system_prompt})
        
        for msg in messages:
            formatted_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

        payload = {
            'model': model,
            'messages': formatted_messages,
            'stream': True,
            'options': {
                'temperature': temperature
            }
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(5, 600)  # 5s connect, 10m read timeout for large models
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                is_done = chunk.get('done', False)
                delta = chunk.get('message', {}).get('content', '')

                metrics = None
                if is_done:
                    total_wall_time = time.time() - start_time
                    total_dur = chunk.get('total_duration')  # ns
                    load_dur = chunk.get('load_duration')    # ns
                    eval_cnt = chunk.get('eval_count')
                    eval_dur = chunk.get('eval_duration')    # ns

                    # Convert nanoseconds to seconds
                    total_s = (total_dur / 1e9) if total_dur else round(total_wall_time, 2)
                    load_s = (load_dur / 1e9) if load_dur else 0.0
                    eval_s = (eval_dur / 1e9) if eval_dur else 0.0
                    tps = round(eval_cnt / eval_s, 1) if (eval_cnt and eval_s > 0) else None

                    metrics = {
                        'total_time': round(total_s, 2),
                        'load_time': round(load_s, 2),
                        'eval_time': round(eval_s, 2),
                        'eval_count': eval_cnt,
                        'tokens_per_second': tps,
                        'model': model
                    }

                yield {
                    'chunk': delta,
                    'done': is_done,
                    'metrics': metrics
                }

        except requests.exceptions.RequestException as e:
            total_wall_time = time.time() - start_time
            yield {
                'chunk': f"\n\n[Error communicating with Ollama: {str(e)}]",
                'done': True,
                'metrics': {
                    'total_time': round(total_wall_time, 2),
                    'error': str(e)
                }
            }


ollama_client = OllamaClient()
