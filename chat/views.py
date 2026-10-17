import json
import os
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseForbidden, Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.conf import settings

from .models import Conversation, Message, UploadedFile, UserProfile
from .forms import UserRegistrationForm, UserLoginForm
from .ollama_client import ollama_client
from .file_parser import extract_text_from_file


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat_home')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'chat_home')
                return redirect(next_url)
            else:
                form.add_error(None, 'Invalid username or password.')
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat_home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat_home')
    else:
        form = UserRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def chat_home(request, conversation_id=None):
    user = request.user
    conversations = Conversation.objects.filter(user=user)
    
    # Dynamic model discovery (cli + api)
    models = ollama_client.get_installed_models()
    if not models:
        default_model = 'llama3:latest'
    else:
        default_model = models[0]

    active_conversation = None
    messages = []
    
    if conversation_id:
        active_conversation = get_object_or_404(Conversation, id=conversation_id, user=user)
        messages = active_conversation.messages.all().prefetch_related('attached_files')

    # Get employee details
    profile = getattr(user, 'profile', None)
    employee_display = f"{user.first_name} {user.last_name}".strip() or user.username
    employee_id = profile.employee_id if profile else ''
    department = profile.department if profile else ''

    context = {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'messages': messages,
        'models': models,
        'default_model': default_model,
        'employee_display': employee_display,
        'employee_id': employee_id,
        'department': department,
        'ollama_healthy': ollama_client.check_health(),
    }
    return render(request, 'chat/index.html', context)


@login_required
@require_GET
def get_models_api(request):
    models = ollama_client.get_installed_models()
    healthy = ollama_client.check_health()
    return JsonResponse({
        'models': models,
        'healthy': healthy
    })


@login_required
@require_POST
def create_conversation(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    model_name = data.get('model_name')
    if not model_name:
        models = ollama_client.get_installed_models()
        model_name = models[0] if models else 'llama3:latest'

    title = data.get('title', 'New Conversation')
    force = data.get('force', False)
    conv = None
    if not force:
        conv = Conversation.objects.filter(
            user=request.user,
            messages__isnull=True
        ).order_by('-created_at').first()

    if conv:
        if model_name and conv.model_name != model_name:
            conv.model_name = model_name
            conv.save(update_fields=['model_name'])
    else:
        conv = Conversation.objects.create(
            user=request.user,
            title=title,
            model_name=model_name
        )

    return JsonResponse({
        'id': str(conv.id),
        'title': conv.title,
        'model_name': conv.model_name,
        'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M')
    })


@login_required
@require_POST
def rename_conversation(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    try:
        data = json.loads(request.body.decode('utf-8'))
        new_title = data.get('title', '').strip()
        if new_title:
            conv.title = new_title[:255]
            conv.save()
            return JsonResponse({'status': 'ok', 'title': conv.title})
        return JsonResponse({'status': 'error', 'message': 'Title cannot be empty'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def delete_conversation(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    conv.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def upload_file_api(request):
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded = request.FILES['file']
    conv_id = request.POST.get('conversation_id')
    conversation = None
    if conv_id:
        conversation = Conversation.objects.filter(id=conv_id, user=request.user).first()

    obj = UploadedFile.objects.create(
        user=request.user,
        conversation=conversation,
        file=uploaded,
        original_name=uploaded.name,
        file_size=uploaded.size
    )

    # Extract text from saved file
    try:
        extracted = extract_text_from_file(obj.file.path, original_filename=uploaded.name)
        obj.extracted_text = extracted
        obj.save(update_fields=['extracted_text'])
    except Exception as e:
        extracted = f"[Error extracting text: {e}]"

    preview_text = extracted[:200] + ('...' if len(extracted) > 200 else '')

    return JsonResponse({
        'id': str(obj.id),
        'name': obj.original_name,
        'size': obj.format_size(),
        'preview': preview_text,
        'char_count': len(extracted)
    })


@login_required
def send_message_stream(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, id=conversation_id, user=request.user)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    prompt = data.get('prompt', '').strip()
    model_name = data.get('model_name') or conv.model_name
    file_ids = data.get('file_ids', [])

    if not prompt and not file_ids:
        return JsonResponse({'error': 'Empty prompt'}, status=400)

    # Update conversation model if changed
    if model_name != conv.model_name:
        conv.model_name = model_name
        conv.save(update_fields=['model_name'])

    # Find attached files
    attached_files = []
    file_context_texts = []
    if file_ids:
        attached_files = list(UploadedFile.objects.filter(id__in=file_ids, user=request.user))
        for f in attached_files:
            file_context_texts.append(
                f"=== DOCUMENT: {f.original_name} ({f.format_size()}) ===\n{f.extracted_text}\n=== END DOCUMENT ==="
            )

    # Save user message
    user_msg = Message.objects.create(
        conversation=conv,
        role='user',
        content=prompt
    )
    if attached_files:
        user_msg.attached_files.set(attached_files)

    # Auto-generate title if this is the first user message
    if conv.title in ['New Chat', 'New Conversation'] or conv.messages.filter(role='user').count() == 1:
        auto_title = prompt.split('\n')[0][:35]
        if len(prompt) > 35:
            auto_title += '...'
        conv.title = auto_title
        conv.save(update_fields=['title'])

    # Build Ollama message history (up to last 12 messages for context)
    past_messages = list(conv.messages.exclude(id=user_msg.id).order_by('created_at')[:12])
    ollama_history = []
    for m in past_messages:
        ollama_history.append({'role': m.role, 'content': m.content})

    # Prepare user content with document context if available
    final_user_content = prompt
    if file_context_texts:
        docs_block = "\n\n".join(file_context_texts)
        final_user_content = f"{docs_block}\n\nUser Question/Instruction:\n{prompt}"

    ollama_history.append({'role': 'user', 'content': final_user_content})

    # Generator for SSE Streaming
    def event_stream():
        full_response = []
        final_metrics = {}

        try:
            for item in ollama_client.stream_chat(
                model=model_name,
                messages=ollama_history,
                system_prompt=conv.system_prompt or "You are a helpful, professional, and knowledgeable AI assistant."
            ):
                chunk = item.get('chunk', '')
                is_done = item.get('done', False)
                metrics = item.get('metrics')

                if chunk:
                    full_response.append(chunk)

                if is_done and metrics:
                    final_metrics = metrics

                payload = {
                    'chunk': chunk,
                    'done': is_done,
                    'metrics': metrics
                }
                yield f"data: {json.dumps(payload)}\n\n"

        except Exception as e:
            err_msg = f"\n\n[Streaming error: {str(e)}]"
            full_response.append(err_msg)
            yield f"data: {json.dumps({'chunk': err_msg, 'done': True, 'error': str(e)})}\n\n"

        # Save assistant message to database
        complete_text = "".join(full_response)
        resp_time = final_metrics.get('total_time')
        eval_cnt = final_metrics.get('eval_count')
        eval_dur = final_metrics.get('eval_time')
        load_dur = final_metrics.get('load_time')
        tps = final_metrics.get('tokens_per_second')

        assistant_msg = Message.objects.create(
            conversation=conv,
            role='assistant',
            content=complete_text,
            response_time=resp_time,
            eval_count=eval_cnt,
            eval_duration=eval_dur,
            load_duration=load_dur,
            tokens_per_second=tps
        )

        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
