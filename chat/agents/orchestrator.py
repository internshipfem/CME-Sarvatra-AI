import os
"""
Orchestrator — coordinates the full document creation flow.
detect → collect fields → generate content → build DOCX → save to DB
"""

import json
import logging
import re
from datetime import datetime

from django.core.files.base import ContentFile

from ..models import GeneratedDocument
from .keyword_detector import detect_document_type, DOCUMENT_TYPE_LABELS
from .field_extractor import (
    auto_fill_sender,
    extract_fields_from_message,
    check_missing_fields,
    get_required_fields,
    get_optional_fields,
)
from .content_generator import generate_content, revise_content
from ..document_engine.docx_builder import build_document

logger = logging.getLogger(__name__)


def clean_subject(raw_subject):
    """Sanitize subject field by removing accidental copy-pasted 'Key Points:' or 'Subject:' labels."""
    if not raw_subject:
        return 'Official Matter'
    s = re.sub(r'(?i)\bkey\s+points\s*:?', '', raw_subject)
    s = re.sub(r'(?i)^subject\s*:?', '', s)
    s = s.strip(' \t\n\r:;,-')
    return s or 'Official Matter'


def generate_reference_number(doc_type, department=''):
    """Auto-generate reference number without stray slashes."""
    clean_dept = re.sub(r'[^A-Za-z0-9]', '', department)[:4].upper() or 'GEN'
    year = datetime.now().year
    count = GeneratedDocument.objects.filter(
        document_type=doc_type,
        created_at__year=year,
    ).count() + 1
    return f"CME/{clean_dept}/{year}/{count:04d}"


def format_date_military():
    """Military date format. No LLM."""
    return datetime.now().strftime("%d %b %Y")


def start_document_session(user, doc_type, initial_message=''):
    """
    Start a document creation session.
    Returns a session dict with auto-filled fields and what's still needed.
    """
    sender_info = auto_fill_sender(user)
    ref_number = generate_reference_number(doc_type, sender_info.get('from_department', ''))
    date_str = format_date_military()

    collected = {
        'from_name': sender_info['from_name'],
        'from_employee_id': sender_info['from_employee_id'],
        'from_department': sender_info['from_department'],
        'reference_number': ref_number,
        'date': date_str,
    }

    if initial_message:
        extracted = extract_fields_from_message(initial_message, doc_type)
        if 'subject' in extracted:
            extracted['subject'] = clean_subject(extracted['subject'])
        collected.update(extracted)

    missing = check_missing_fields(doc_type, collected)

    return {
        'doc_type': doc_type,
        'doc_type_label': DOCUMENT_TYPE_LABELS.get(doc_type, doc_type),
        'collected_fields': collected,
        'missing_fields': [
            {'name': name, 'label': info['label'], 'prompt': info['prompt']}
            for name, info in missing
        ],
        'auto_filled': {
            'from_name': sender_info['from_name'],
            'date': date_str,
            'reference_number': ref_number,
        },
        'ready': len(missing) == 0,
    }


def process_field_response(session_data, field_values):
    """Process user's field responses and update the session."""
    collected = session_data.get('collected_fields', {})
    if 'subject' in field_values:
        field_values['subject'] = clean_subject(field_values['subject'])
    collected.update(field_values)

    doc_type = session_data['doc_type']
    missing = check_missing_fields(doc_type, collected)

    session_data['collected_fields'] = collected
    session_data['missing_fields'] = [
        {'name': name, 'label': info['label'], 'prompt': info['prompt']}
        for name, info in missing
    ]
    session_data['ready'] = len(missing) == 0

    return session_data


def create_document(user, session_data, model_name=None, conversation=None):
    """
    Full document creation: LLM generates content → python-docx builds DOCX → saves to DB.
    """
    doc_type = session_data['doc_type']
    fields = session_data['collected_fields']

    # Clean subject
    if 'subject' in fields:
        fields['subject'] = clean_subject(fields['subject'])

    # Step 0: Resolve digital signature asset image
    sig_asset_id = fields.get('_signature_asset_id')
    sig_asset = None
    if sig_asset_id and sig_asset_id != 'none':
        try:
            from ..models import SignatureAsset
            sig_asset = SignatureAsset.objects.get(id=sig_asset_id, user=user)
            if sig_asset.image and os.path.exists(sig_asset.image.path):
                fields['_signature_image_path'] = sig_asset.image.path
        except Exception:
            pass
    elif not fields.get('_no_signature'):
        try:
            from ..models import SignatureAsset
            sig_asset = SignatureAsset.objects.filter(user=user, is_default=True).first()
            if sig_asset and sig_asset.image and os.path.exists(sig_asset.image.path):
                fields['_signature_image_path'] = sig_asset.image.path
        except Exception:
            pass

    # Step 1: Generate content via LLM (or smart military naturalizer fallback)
    result = generate_content(doc_type, fields, model_name=model_name)
    generated_text = result['content']

    # Step 2: Build DOCX file
    docx_bytes = build_document(doc_type, fields, generated_text)

    # Step 3: Save to database
    title = fields.get('subject') or fields.get('meeting_title') or fields.get('title') or 'Untitled Document'
    filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

    doc = GeneratedDocument.objects.create(
        user=user,
        conversation=conversation,
        document_type=doc_type,
        title=title,
        fields_json=json.dumps(fields, default=str),
        generated_content=generated_text,
        model_used=result['model'],
        generation_time=result['generation_time'],
        file_size=len(docx_bytes),
        signature_asset=sig_asset,
    )
    doc.file.save(filename, ContentFile(docx_bytes), save=True)

    return {
        'document_id': str(doc.id),
        'title': title,
        'doc_type': doc_type,
        'doc_type_label': DOCUMENT_TYPE_LABELS.get(doc_type, doc_type),
        'generated_content': generated_text,
        'model_used': result['model'],
        'generation_time': result['generation_time'],
        'file_size': doc.format_size(),
        'filename': filename,
        'version': doc.version,
        'is_locked': doc.is_locked,
        'lock_hint': doc.lock_hint,
        'encrypt_export': doc.encrypt_export,
        'is_final': doc.is_final,
        'download_url': f"/api/documents/{doc.id}/download/",
        'pdf_download_url': f"/api/documents/{doc.id}/pdf/",
    }


def revise_document(document_id, revision_instruction, user):
    """Revise an existing document via user instruction, or retry fresh if instruction is empty."""
    original = GeneratedDocument.objects.get(id=document_id, user=user)
    try:
        original_fields = json.loads(original.fields_json) if original.fields_json else {}
    except Exception:
        original_fields = {}

    revision_instruction = (revision_instruction or '').strip()

    if revision_instruction:
        # LLM revision call applying user's modification instructions
        result = revise_content(
            original.generated_content,
            revision_instruction,
            model_name=original.model_used,
        )
    else:
        # Fresh retry generation with the same fields
        result = generate_content(
            original.document_type,
            original_fields,
            model_name=original.model_used,
        )

    new_text = result['content']
    docx_bytes = build_document(original.document_type, original_fields, new_text)

    filename = f"{original.document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v{original.version + 1}.docx"

    doc = GeneratedDocument.objects.create(
        user=user,
        conversation=original.conversation,
        document_type=original.document_type,
        title=original.title,
        fields_json=original.fields_json,
        generated_content=new_text,
        model_used=result['model'],
        generation_time=result['generation_time'],
        file_size=len(docx_bytes),
        version=original.version + 1,
        is_locked=original.is_locked,
        pin_hash=original.pin_hash,
        lock_hint=original.lock_hint,
        encrypt_export=original.encrypt_export,
        is_final=original.is_final,
        signature_asset=original.signature_asset,
    )
    doc.file.save(filename, ContentFile(docx_bytes), save=True)

    return {
        'document_id': str(doc.id),
        'title': doc.title,
        'doc_type': doc.document_type,
        'doc_type_label': DOCUMENT_TYPE_LABELS.get(doc.document_type, doc.document_type),
        'generated_content': new_text,
        'model_used': result['model'],
        'generation_time': result['generation_time'],
        'file_size': doc.format_size(),
        'filename': filename,
        'version': doc.version,
        'is_locked': doc.is_locked,
        'lock_hint': doc.lock_hint,
        'encrypt_export': doc.encrypt_export,
        'is_final': doc.is_final,
        'download_url': f"/api/documents/{doc.id}/download/",
        'pdf_download_url': f"/api/documents/{doc.id}/pdf/",
    }
