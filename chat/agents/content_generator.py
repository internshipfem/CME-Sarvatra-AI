"""
Content Generator — THE one LLM call per document.
Uses the existing ollama_client singleton. Collects the full streamed response.
Includes an intelligent military staff drafting engine when Ollama is offline.
"""

import re
import time
import logging

from ..ollama_client import ollama_client
from .prompts import SYSTEM_PROMPT, build_content_prompt, build_revision_prompt

logger = logging.getLogger(__name__)


def clean_subject_text(text):
    if not text:
        return 'the designated requirement'
    cleaned = re.sub(r'(?i)\bkey\s+points\s*:?', '', text)
    cleaned = re.sub(r'(?i)^subject\s*:?', '', cleaned)
    return cleaned.strip(' \t\n\r:;,-')


def naturalize_military_sentence(raw_text):
    """
    Converts a rough bullet point into an articulate, grammatically complete
    military staff sentence with appropriate formal phrasing.
    """
    text = raw_text.strip().lstrip('0123456789.-*• \t').strip().rstrip('. \t\n')
    if not text:
        return ""

    first_char = text[0].upper()
    text = first_char + text[1:] if len(text) > 1 else first_char
    lower = text.lower()

    # If it's already a full sentence, leave it
    if lower.startswith(('it is ', 'it was ', 'reference is ', 'in accordance with ', 'accordingly,', 'all requisite', 'furthermore,', 'in order to')):
        return text + '.'

    # Transform into professional military active/formal clauses
    if any(k in lower for k in ['requisition', 'procure', 'purchase', 'requirement', 'sanction of', 'need', 'issue of']):
        if lower.startswith(('requisition of ', 'requisition for ')):
            rest = text[len('requisition of '):].strip()
            return f"Accordingly, requisition is hereby submitted for {rest}."
        return f"Accordingly, requisition is hereby submitted for {text[0].lower() + text[1:]}."

    elif any(k in lower for k in ['schedule', 'conduct', 'organize', 'date', 'held', 'commence']):
        t_clean = text[0].lower() + text[1:]
        if 'scheduled for' in lower and ' is scheduled' not in lower:
            t_clean = t_clean.replace('scheduled for', 'is scheduled to take place in')
        return f"It is submitted that the {t_clean}."

    elif any(k in lower for k in ['safety', 'clearance', 'protocol', 'guideline', 'sop', 'standard', 'precaution']):
        t_clean = text[0].lower() + text[1:]
        t_clean = re.sub(r'\s+requested$', '', t_clean)
        return f"All mandatory {t_clean} have been coordinated and shall be strictly adhered to."

    elif any(k in lower for k in ['inspect', 'audit', 'trial', 'test', 'evaluat']):
        return f"Comprehensive technical evaluation and {text[0].lower() + text[1:]}."

    elif any(k in lower for k in ['deadline', 'timeline', 'completion', 'timeframe', 'urgent', 'priority']):
        return f"In view of operational urgency, {text[0].lower() + text[1:]}."

    else:
        return f"It is further submitted that {text[0].lower() + text[1:]}."


def generate_fallback_paragraphs(doc_type, fields):
    """
    High-caliber offline military drafting engine:
    Generates structured, professional military paragraphs from user input.
    """
    subject = clean_subject_text(fields.get('subject') or fields.get('title') or fields.get('meeting_title'))
    key_points = fields.get('key_points') or fields.get('agenda_items') or ''

    paragraphs = []

    if doc_type == 'formal_letter':
        paragraphs.append(
            f"1. Reference is made to the operational requirements and training curriculum regarding {subject}."
        )

        if key_points:
            points = [p.strip() for p in key_points.split('\n') if p.strip()]
            for idx, pt in enumerate(points, start=2):
                sentence = naturalize_military_sentence(pt)
                if sentence:
                    paragraphs.append(f"{idx}. {sentence}")
            
            call_to_action_idx = len(paragraphs) + 1
            paragraphs.append(
                f"{call_to_action_idx}. In view of the above, administrative and technical sanction of the competent authority is requested to proceed with necessary arrangements."
            )
        else:
            paragraphs.append(
                "2. It is submitted that all operational specifications and resource allocations have been thoroughly reviewed by the technical committee."
            )
            paragraphs.append(
                "3. In view of the above, administrative and technical sanction of the competent authority is requested to proceed with necessary arrangements."
            )

    elif doc_type == 'office_memo':
        paragraphs.append(
            f"1. This memorandum is issued to draw attention to {subject} across all concerned branches."
        )
        if key_points:
            points = [p.strip() for p in key_points.split('\n') if p.strip()]
            for idx, pt in enumerate(points, start=2):
                sentence = naturalize_military_sentence(pt)
                if sentence:
                    paragraphs.append(f"{idx}. {sentence}")
        paragraphs.append(
            f"{len(paragraphs) + 1}. Strict compliance with the above instructions shall be ensured by all department heads."
        )

    elif doc_type == 'meeting_minutes':
        paragraphs.append(
            f"1. A review meeting was convened on {fields.get('date', 'the scheduled date')} to deliberate upon {subject}."
        )
        if key_points:
            points = [p.strip() for p in key_points.split('\n') if p.strip()]
            for idx, pt in enumerate(points, start=2):
                clean_pt = pt.lstrip('0123456789.-*• \t')
                paragraphs.append(f"{idx}. Discussion & Resolution: {clean_pt}")
        paragraphs.append(
            f"{len(paragraphs) + 1}. The meeting concluded with instructions to the respective project officers to submit progress reports as per timelines."
        )

    elif doc_type == 'office_note':
        paragraphs.append(
            f"1. Background: Reference is placed below concerning {subject}."
        )
        if key_points:
            points = [p.strip() for p in key_points.split('\n') if p.strip()]
            if len(points) >= 1:
                paragraphs.append(f"2. Current Situation: {naturalize_military_sentence(points[0])}")
            if len(points) >= 2:
                paragraphs.append(f"3. Proposal: {naturalize_military_sentence(points[1])}")
            if len(points) >= 3:
                paragraphs.append(f"4. Justification: {naturalize_military_sentence(points[2])}")
        paragraphs.append(
            f"{len(paragraphs) + 1}. Recommendation: Put up for favorable consideration and sanction of the competent authority, please."
        )

    elif doc_type == 'leave_application':
        leave_type = fields.get('leave_type') or 'Casual Leave'
        from_date = fields.get('from_date') or fields.get('date') or 'the requested date'
        to_date = fields.get('to_date') or 'the designated date'
        reason = fields.get('key_points') or 'urgent personal and family obligations'

        paragraphs.append(
            f"1. It is respectfully submitted that the undersigned wishes to proceed on {leave_type} "
            f"with effect from {from_date} to {to_date} (both days inclusive)."
        )
        paragraphs.append(
            f"2. The purpose of proceeding on leave is: {naturalize_military_sentence(reason)}"
        )
        paragraphs.append(
            "3. It is confirmed that all pending staff duties and urgent correspondence have been cleared or handed over to the designated relieving officer."
        )
        paragraphs.append(
            "4. In view of the above, it is requested that necessary sanction for the aforementioned leave may kindly be accorded, please."
        )

    else:
        # Default / Office Order / Technical Report
        paragraphs.append(
            f"1. In exercise of delegated administrative authority, instructions are hereby promulgated regarding {subject}."
        )
        if key_points:
            points = [p.strip() for p in key_points.split('\n') if p.strip()]
            for idx, pt in enumerate(points, start=2):
                paragraphs.append(f"{idx}. {naturalize_military_sentence(pt)}")
        paragraphs.append(
            f"{len(paragraphs) + 1}. All concerned personnel shall adhere strictly to the stipulated instructions."
        )

    return "\n\n".join(paragraphs)


def _apply_offline_revision(original_content, instruction):
    """
    Rule-based offline revision engine. Handles the most common military document
    revision requests without requiring Ollama connectivity.
    """
    if not instruction:
        return original_content

    inst_lower = instruction.lower().strip()

    # 1. Date change
    date_match = re.search(
        r'(?:change|update|set|make)\s+(?:the\s+)?date\s+(?:to\s+)?([0-9]{1,2}\s+\w+\s+[0-9]{4}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
        inst_lower
    )
    if date_match:
        new_date = date_match.group(1).title()
        revised = re.sub(
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
            new_date, original_content, flags=re.IGNORECASE
        )
        if revised != original_content:
            return revised

    # 2. Make shorter / concise
    if any(k in inst_lower for k in ['shorter', 'concise', 'brief', 'trim', 'reduce', 'condense']):
        paras = [p.strip() for p in original_content.split('\n\n') if p.strip()]
        if len(paras) > 3:
            kept = [paras[0]] + paras[2:-1:2] + [paras[-1]]
            # Re-index paragraphs cleanly
            reindexed = []
            for i, p in enumerate(kept, 1):
                clean_p = re.sub(r'^\d+\.\s*', '', p)
                reindexed.append(f"{i}. {clean_p}")
            return '\n\n'.join(reindexed)

    # 3. Make more formal / authoritative
    if any(k in inst_lower for k in ['formal', 'authoritative', 'official', 'strict']):
        revised = original_content
        informal_map = {
            'we need': 'it is essential',
            'we want': 'it is desired',
            'please': 'it is requested that',
            'asap': 'with immediate effect',
            'as soon as possible': 'at the earliest',
            "don't": 'shall not',
            'can not': 'cannot',
            'tell us': 'intimate this Headquarters',
        }
        for informal, formal in informal_map.items():
            revised = re.sub(r'\b' + re.escape(informal) + r'\b', formal, revised, flags=re.IGNORECASE)
        return revised

    # 4. Add a paragraph regarding topic
    add_match = re.search(r'add\s+(?:a\s+)?(?:para(?:graph)?\s+(?:about|on|regarding)\s+)?(.+)', instruction, flags=re.IGNORECASE)
    if add_match and len(instruction.strip()) > 6:
        topic = add_match.group(1).strip().rstrip('.')
        paras = [p.strip() for p in original_content.split('\n\n') if p.strip()]
        para_num = len(paras) + 1
        new_para = (
            f"{para_num}. It is further submitted that due consideration has been given to {topic}. "
            f"Necessary action in this regard shall be initiated in accordance with standing operating procedures."
        )
        return original_content + '\n\n' + new_para

    # 5. Default amendment append
    paras = [p.strip() for p in original_content.split('\n\n') if p.strip()]
    para_num = len(paras) + 1
    clean_inst = instruction.strip().rstrip('.')
    return (
        original_content + '\n\n'
        f"{para_num}. Amendment: {clean_inst[0].upper() + clean_inst[1:]}."
    )


def generate_content(doc_type, fields, model_name=None):
    """
    Make ONE LLM call to generate document body content.
    Returns dict with 'content', 'model', 'generation_time', 'metrics'.
    Falls back gracefully to the intelligent military drafting engine if Ollama is offline.
    """
    if 'subject' in fields:
        fields['subject'] = clean_subject_text(fields['subject'])

    prompt = build_content_prompt(doc_type, fields)

    if not model_name:
        models = ollama_client.get_installed_models()
        model_name = models[0] if models else 'llama3:latest'

    # Check Ollama health before streaming
    if not ollama_client.check_health():
        logger.info("Ollama is offline. Generating structured military draft.")
        fallback_text = generate_fallback_paragraphs(doc_type, fields)
        return {
            'content': fallback_text,
            'model': f"{model_name} (military engine)",
            'generation_time': 0.1,
            'metrics': {'total_time': 0.1, 'offline': True},
        }

    messages = [{'role': 'user', 'content': prompt}]

    start_time = time.time()
    full_response = []
    final_metrics = {}

    try:
        for item in ollama_client.stream_chat(
            model=model_name,
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ):
            chunk = item.get('chunk', '')
            if chunk:
                full_response.append(chunk)

            if item.get('done') and item.get('metrics'):
                final_metrics = item['metrics']
    except Exception as e:
        logger.warning(f"Ollama stream exception: {e}")

    generation_time = time.time() - start_time
    content = ''.join(full_response).strip()

    # If stream returned an error message, fall back to smart engine
    if not content or content.startswith('[Error communicating with Ollama'):
        logger.warning("Ollama call failed. Utilizing military drafting engine.")
        content = generate_fallback_paragraphs(doc_type, fields)
        model_name = f"{model_name} (military engine)"

    logger.info(f"Generated {doc_type} content in {generation_time:.1f}s using {model_name}")

    return {
        'content': content,
        'model': model_name,
        'generation_time': round(generation_time, 2),
        'metrics': final_metrics,
    }


def revise_content(original_content, revision_instruction, model_name=None):
    """
    Make ONE LLM call to revise existing document content.
    """
    if not model_name:
        models = ollama_client.get_installed_models()
        model_name = models[0] if models else 'llama3:latest'

    if not ollama_client.check_health():
        revised = _apply_offline_revision(original_content, revision_instruction)
        return {
            'content': revised,
            'model': f"{model_name} (military engine)",
            'generation_time': 0.1,
            'metrics': {'total_time': 0.1},
        }

    prompt = build_revision_prompt(original_content, revision_instruction)
    messages = [{'role': 'user', 'content': prompt}]

    start_time = time.time()
    full_response = []
    final_metrics = {}

    try:
        for item in ollama_client.stream_chat(
            model=model_name,
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ):
            chunk = item.get('chunk', '')
            if chunk:
                full_response.append(chunk)

            if item.get('done') and item.get('metrics'):
                final_metrics = item['metrics']
    except Exception as e:
        logger.warning(f"Ollama revision stream exception: {e}")

    generation_time = time.time() - start_time
    content = ''.join(full_response).strip()

    if not content or content.startswith('[Error communicating with Ollama'):
        content = _apply_offline_revision(original_content, revision_instruction)

    logger.info(f"Revised content in {generation_time:.1f}s using {model_name}")

    return {
        'content': content,
        'model': model_name,
        'generation_time': round(generation_time, 2),
        'metrics': final_metrics,
    }
