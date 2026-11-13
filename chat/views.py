import json
import os
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseForbidden, Http404, FileResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Conversation, Message, UploadedFile, UserProfile, GeneratedDocument
from .forms import UserRegistrationForm, UserLoginForm
from .ollama_client import ollama_client
from .file_parser import extract_text_from_file

# Document Agent & Engine imports
from .agents.keyword_detector import (
    detect_document_type,
    get_all_document_types,
    DOCUMENT_TYPE_LABELS,
    DOCUMENT_TYPE_ICONS,
)
from .agents.field_extractor import (
    get_required_fields,
    get_optional_fields,
)
from .agents.orchestrator import (
    start_document_session,
    process_field_response,
    create_document,
    revise_document,
)


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

    # Get employee & officer details
    profile, _ = UserProfile.objects.get_or_create(user=user)
    employee_display = f"{user.first_name} {user.last_name}".strip() or user.username
    employee_id = profile.employee_id
    department = profile.department or 'Combat Engineering Wing'
    rank = profile.rank or ''
    appointment = profile.appointment or ''
    authority = profile.authority or ''
    signature_style = profile.signature_style or 'military'
    signature_text = profile.signature_text or ''

    # Get recent generated documents for quick access
    recent_documents = GeneratedDocument.objects.filter(user=user)[:10]

    context = {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'messages': messages,
        'models': models,
        'default_model': default_model,
        'employee_display': employee_display,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'employee_id': employee_id,
        'department': department,
        'rank': rank,
        'appointment': appointment,
        'authority': authority,
        'signature_style': signature_style,
        'signature_text': signature_text,
        'ollama_healthy': ollama_client.check_health(),
        'recent_documents': recent_documents,
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
        new_title = ''
        try:
            data = json.loads(request.body.decode('utf-8'))
            new_title = data.get('title', '').strip()
        except Exception:
            new_title = request.POST.get('title', '').strip()

        if new_title:
            conv.title = new_title[:255]
            conv.save(update_fields=['title'])
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
        content=prompt or (f"Analyze attached document: {attached_files[0].original_name}" if attached_files else "")
    )
    if attached_files:
        user_msg.attached_files.set(attached_files)

    # Auto-generate title if this is the first user message
    if conv.title in ['New Chat', 'New Conversation'] or conv.messages.filter(role='user').count() == 1:
        title_source = prompt or (attached_files[0].original_name if attached_files else "New Conversation")
        auto_title = title_source.split('\n')[0][:35]
        if len(title_source) > 35:
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
        effective_prompt = prompt or "Please thoroughly analyze the attached document(s), summarize the key contents, and answer any specific points."
        final_user_content = (
            f"[ATTACHED DOCUMENTS CONTENT]\n"
            f"The following text has been extracted from the user's uploaded document(s). "
            f"Analyze and use this provided text to answer the user request:\n\n"
            f"{docs_block}\n\n"
            f"[END OF ATTACHED DOCUMENTS]\n\n"
            f"User Question / Instruction:\n{effective_prompt}"
        )

    ollama_history.append({'role': 'user', 'content': final_user_content})

    # Dynamic Document Modification: Check if query modifies active document
    active_doc = GeneratedDocument.objects.filter(conversation=conv).order_by('-created_at').first()
    if not active_doc:
        active_doc = GeneratedDocument.objects.filter(user=request.user).order_by('-created_at').first()

    prompt_lower = (prompt or '').lower()
    doc_mod_triggers = [
        'change date', 'update date', 'set date',
        'change letterhead', 'update letterhead', 'set letterhead',
        'change wing', 'change faculty', 'change formation',
        'change subject', 'update subject', 'change title',
        'change recipient', 'change addressee', 'change to_name', 'change the recipient',
        'make it formal', 'more formal', 'make it shorter', 'make it concise',
        'add a paragraph', 'add para', 'add point',
        'revise the document', 'revise letter', 'revise memo', 'revise doc',
        'mark as secret', 'mark as confidential', 'change classification'
    ]
    is_doc_mod = bool(active_doc and any(t in prompt_lower for t in doc_mod_triggers))
    revised_doc_payload = None

    if is_doc_mod and active_doc:
        try:
            from chat.agents.orchestrator import revise_document
            revised_doc_payload = revise_document(active_doc.id, prompt, user=request.user)
            rev_obj = GeneratedDocument.objects.get(id=revised_doc_payload['document_id'])
            if not rev_obj.conversation:
                rev_obj.conversation = conv
                rev_obj.save(update_fields=['conversation'])
        except Exception as e:
            is_doc_mod = False
            revised_doc_payload = None

    # Generator for SSE Streaming
    def event_stream():
        full_response = []
        final_metrics = {}

        if is_doc_mod and revised_doc_payload:
            ack_msg = (
                f"**Official Document Updated (Version {revised_doc_payload['version']})**\n\n"
                f"Applied instruction: *\"{prompt.strip()}\"*\n\n"
                f"- **Title / Subject:** {revised_doc_payload.get('title', 'Official Document')}\n"
                f"- **Document Type:** {revised_doc_payload.get('doc_type_label', '')}\n"
                f"- **Files Updated:** Word DOCX and PDF recompiled with new parameters.\n\n"
                f"---\n\n"
                f"{revised_doc_payload.get('generated_content', '')}"
            )
            full_response.append(ack_msg)
            yield f"data: {json.dumps({'chunk': ack_msg})}\n\n"
            yield f"data: {json.dumps({'done': True, 'metrics': {'total_time': 0.15}, 'doc_updated': revised_doc_payload})}\n\n"
            Message.objects.create(conversation=conv, role='assistant', content=ack_msg)
            return

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


# ==============================================================================
# DOCUMENT CREATION AGENT API ENDPOINTS
# Minimal LLM usage — 1 LLM call for generation, everything else in Python
# ==============================================================================

@login_required
@require_GET
def list_document_types_api(request):
    """Return available document types with labels, icons, and fields."""
    types = get_all_document_types()
    for t in types:
        t['required_fields'] = get_required_fields(t['type'])
        t['optional_fields'] = get_optional_fields(t['type'])
    return JsonResponse({'document_types': types})


@login_required
@require_POST
def detect_document_type_api(request):
    """Detect document type from user input string via keyword regex (0 LLM calls)."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}
    message = data.get('message', '').strip()
    doc_type, confidence = detect_document_type(message)
    label = DOCUMENT_TYPE_LABELS.get(doc_type, '') if doc_type else ''
    icon = DOCUMENT_TYPE_ICONS.get(doc_type, '') if doc_type else ''
    return JsonResponse({
        'doc_type': doc_type,
        'confidence': confidence,
        'label': label,
        'icon': icon,
    })


@login_required
@require_POST
def start_document_session_api(request):
    """Initialize a document session with profile defaults and check missing fields (0 LLM calls)."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}
    doc_type = data.get('doc_type', 'formal_letter')
    initial_message = data.get('initial_message', '')
    session = start_document_session(request.user, doc_type, initial_message)
    return JsonResponse(session)


@login_required
@require_POST
def generate_document_api(request):
    """Run single-LLM generation and assemble DOCX (1 LLM call)."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    doc_type = data.get('doc_type')
    collected_fields = data.get('collected_fields', {})
    model_name = data.get('model_name')
    conversation_id = data.get('conversation_id')

    if not doc_type or not collected_fields:
        return JsonResponse({'error': 'Missing doc_type or collected_fields'}, status=400)

    conversation = None
    if conversation_id:
        conversation = Conversation.objects.filter(id=conversation_id, user=request.user).first()

    # Process selected signature asset
    sig_id = data.get('signature_asset_id', '').strip()
    if sig_id:
        collected_fields['_signature_asset_id'] = sig_id
    elif data.get('no_signature'):
        collected_fields['_signature_asset_id'] = 'none'
        collected_fields['_no_signature'] = True

    session_data = {
        'doc_type': doc_type,
        'collected_fields': collected_fields,
    }

    security_pin = data.get('security_pin', '').strip()
    lock_hint = data.get('lock_hint', '').strip()
    encrypt_export = bool(data.get('encrypt_export', False))

    try:
        doc_info = create_document(
            user=request.user,
            session_data=session_data,
            model_name=model_name,
            conversation=conversation,
        )

        if security_pin and len(security_pin) >= 4:
            doc_obj = GeneratedDocument.objects.get(id=doc_info['document_id'])
            doc_obj.set_lock_pin(security_pin, hint=lock_hint, encrypt_export=encrypt_export)
            request.session[f'unlocked_doc_{doc_obj.id}'] = True
            doc_info['is_locked'] = True
            doc_info['lock_hint'] = lock_hint
            doc_info['encrypt_export'] = encrypt_export

        # Record assistant card message in conversation if present
        if conversation:
            card_content = (
                f"### 📄 {doc_info['doc_type_label']}: {doc_info['title']}\n\n"
                f"{doc_info['generated_content']}\n\n"
                f"**[Download Document ({doc_info['file_size']})]({doc_info['download_url']})**"
            )
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=card_content,
                response_time=doc_info.get('generation_time'),
            )
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])

        return JsonResponse({'status': 'ok', 'document': doc_info})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def revise_document_api(request, document_id):
    """Revise an existing document via single LLM revision call or fresh retry."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    instruction = data.get('instruction', '').strip()

    try:
        doc_info = revise_document(document_id, instruction, user=request.user)
        return JsonResponse({'status': 'ok', 'document': doc_info})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def update_document_text_api(request, document_id):
    """Update document body content directly from preview editor and rebuild DOCX (0 LLM calls)."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Document content cannot be empty'}, status=400)

    try:
        fields = json.loads(doc.fields_json) if doc.fields_json else {}
    except Exception:
        fields = {}

    incoming_fields = data.get('fields')
    if isinstance(incoming_fields, dict):
        fields.update(incoming_fields)
        doc.fields_json = json.dumps(fields)
        new_title = fields.get('subject') or fields.get('title') or fields.get('meeting_title')
        if new_title:
            doc.title = str(new_title)[:255]

    from chat.document_engine.docx_builder import build_document
    docx_bytes = build_document(doc.document_type, fields, content)

    doc.generated_content = content
    doc.file_size = len(docx_bytes)

    filename = os.path.basename(doc.file.name) if doc.file else f"{doc.document_type}_{doc.id}.docx"
    doc.file.save(filename, ContentFile(docx_bytes), save=False)
    doc.save(update_fields=['generated_content', 'file_size', 'file', 'fields_json', 'title'])

    return JsonResponse({
        'status': 'ok',
        'document_id': str(doc.id),
        'file_size': doc.format_size(),
        'title': doc.title,
        'download_url': f"/api/documents/{doc.id}/download/",
        'pdf_download_url': f"/api/documents/{doc.id}/pdf/",
    })


@login_required
@require_GET
def download_document_api(request, document_id):
    """Download generated DOCX file with optional passcode encryption (0 LLM calls)."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)
    if not doc.file or not os.path.exists(doc.file.path):
        raise Http404("Document file not found on disk")

    pin_attempt = request.GET.get('pin') or request.GET.get('passcode') or ''
    is_session_unlocked = request.session.get(f'unlocked_doc_{doc.id}', False)

    # Check In-App PIN lock if locked
    if doc.is_locked and not is_session_unlocked:
        if not pin_attempt or not doc.check_lock_pin(pin_attempt):
            return JsonResponse({'error': 'Document is PIN-locked. Valid passcode required.'}, status=403)
        request.session[f'unlocked_doc_{doc.id}'] = True

    # Check if clean decrypted export was requested
    is_decrypted = request.GET.get('decrypted') in ('1', 'true', 'yes') or request.GET.get('plain') in ('1', 'true', 'yes')

    # Determine encryption password
    enc_password = None
    if not is_decrypted:
        if request.GET.get('passcode'):
            enc_password = request.GET.get('passcode').strip()
        elif request.GET.get('encrypted') in ('1', 'true') and pin_attempt:
            enc_password = pin_attempt.strip()
        elif doc.is_locked and doc.encrypt_export and not is_session_unlocked and pin_attempt:
            enc_password = pin_attempt.strip()

    if enc_password and enc_password.strip():
        try:
            from msoffcrypto.method.ecma376_agile import ECMA376Agile
            from django.http import HttpResponse

            with open(doc.file.path, 'rb') as f:
                enc_bytes = ECMA376Agile.encrypt(enc_password.strip(), f)

            response = HttpResponse(
                enc_bytes,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            base_filename = os.path.basename(doc.file.name)
            response['Content-Disposition'] = f'attachment; filename="{base_filename}"'
            return response
        except Exception as e:
            # Fallback to standard file response if encryption fails
            pass

    return FileResponse(
        open(doc.file.path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(doc.file.name),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )




@login_required
@require_GET
@xframe_options_sameorigin
def download_pdf_api(request, document_id):
    """Download generated document as military-standard A4 PDF with optional AES-256 encryption."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)

    pin_attempt = request.GET.get('pin') or request.GET.get('passcode') or ''
    is_session_unlocked = request.session.get(f'unlocked_doc_{doc.id}', False)

    # Check In-App PIN lock if locked
    if doc.is_locked and not is_session_unlocked:
        if not pin_attempt or not doc.check_lock_pin(pin_attempt):
            return JsonResponse({'error': 'Document is PIN-locked. Valid passcode required.'}, status=403)
        request.session[f'unlocked_doc_{doc.id}'] = True

    # Check if clean decrypted export was requested
    is_decrypted = request.GET.get('decrypted') in ('1', 'true', 'yes') or request.GET.get('plain') in ('1', 'true', 'yes')

    # Determine encryption password
    enc_password = None
    if not is_decrypted:
        if request.GET.get('passcode'):
            enc_password = request.GET.get('passcode').strip()
        elif request.GET.get('encrypted') in ('1', 'true') and pin_attempt:
            enc_password = pin_attempt.strip()
        elif doc.is_locked and doc.encrypt_export and not is_session_unlocked and pin_attempt:
            enc_password = pin_attempt.strip()

    try:
        fields = json.loads(doc.fields_json) if doc.fields_json else {}
    except Exception:
        fields = {}

    # Attach draft status & signature image path
    fields['_is_draft'] = not doc.is_final
    fields['is_final'] = doc.is_final
    if doc.signature_asset and doc.signature_asset.image and os.path.exists(doc.signature_asset.image.path):
        fields['_signature_image_path'] = doc.signature_asset.image.path
    elif fields.get('_signature_asset_id') and fields['_signature_asset_id'] != 'none':
        try:
            from chat.models import SignatureAsset
            sig = SignatureAsset.objects.get(id=fields['_signature_asset_id'], user=request.user)
            if sig.image and os.path.exists(sig.image.path):
                fields['_signature_image_path'] = sig.image.path
        except Exception:
            pass

    import re
    from chat.document_engine.pdf_builder import build_pdf_document

    try:
        pdf_bytes = build_pdf_document(
            doc_type=doc.document_type,
            fields=fields,
            body_content=doc.generated_content or '',
            passcode=enc_password
        )
    except Exception as e:
        return JsonResponse({'error': f'PDF generation failed: {str(e)}'}, status=500)

    clean_title = re.sub(r'[^A-Za-z0-9_\-\.]', '_', doc.title or doc.document_type)[:50]
    filename = f"{clean_title}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    is_inline = request.GET.get('preview') in ('1', 'true') or request.GET.get('inline') in ('1', 'true')
    disposition = 'inline' if is_inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@login_required
@require_POST
def toggle_document_lock_api(request, document_id):
    """Set or remove PIN lock and export encryption for a document."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    action = data.get('action', 'lock')
    pin = data.get('pin', '').strip()
    hint = data.get('hint', '').strip()
    encrypt_export = bool(data.get('encrypt_export', True))

    if action == 'lock':
        if len(pin) < 4:
            return JsonResponse({'error': 'Security PIN / Passcode must be at least 4 characters'}, status=400)
        doc.set_lock_pin(pin, hint=hint, encrypt_export=encrypt_export)
        request.session[f'unlocked_doc_{doc.id}'] = True
        return JsonResponse({
            'status': 'ok',
            'is_locked': True,
            'encrypt_export': doc.encrypt_export,
            'lock_hint': doc.lock_hint,
            'message': 'Document locked with military security PIN.'
        })
    elif action == 'unlock':
        is_session_unlocked = request.session.get(f'unlocked_doc_{doc.id}', False)
        # Allow unlock if current session is already authenticated OR if correct PIN is provided
        if not is_session_unlocked and not doc.check_lock_pin(pin):
            return JsonResponse({'error': 'Incorrect PIN. Cannot remove security lock.'}, status=403)
        doc.remove_lock()
        request.session.pop(f'unlocked_doc_{doc.id}', None)
        return JsonResponse({
            'status': 'ok',
            'is_locked': False,
            'encrypt_export': False,
            'message': 'Security lock removed successfully.'
        })
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)


@login_required
@require_POST
def verify_document_pin_api(request, document_id):
    """Verify PIN for locked document access. Locks out for 5 minutes after 5 failed attempts."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)

    fail_key = f'pin_fails_{document_id}'
    lockout_key = f'pin_lockout_{document_id}'

    lockout_until = request.session.get(lockout_key, 0)
    now_ts = time.time()
    if lockout_until and now_ts < lockout_until:
        remaining = int((lockout_until - now_ts) / 60) + 1
        return JsonResponse(
            {'error': f'Too many incorrect attempts. Security lockout active. Try again in {remaining} minute(s).'},
            status=429
        )

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    pin = data.get('pin', '').strip()
    if not doc.check_lock_pin(pin):
        fails = request.session.get(fail_key, 0) + 1
        request.session[fail_key] = fails
        if fails >= 5:
            request.session[lockout_key] = time.time() + 300  # 5 minutes
            request.session[fail_key] = 0
            return JsonResponse(
                {'error': 'Too many incorrect attempts. Document locked for 5 minutes for security protection.'},
                status=429
            )
        return JsonResponse(
            {'error': f'Incorrect Security PIN. Access denied. ({fails}/5 attempts)'},
            status=403
        )

    # Success — clear counters
    request.session.pop(fail_key, None)
    request.session.pop(lockout_key, None)
    request.session[f'unlocked_doc_{doc.id}'] = True

    try:
        fields = json.loads(doc.fields_json) if doc.fields_json else {}
    except Exception:
        fields = {}

    return JsonResponse({
        'status': 'ok',
        'document': {
            'document_id': str(doc.id),
            'title': doc.title,
            'doc_type': doc.document_type,
            'doc_type_label': DOCUMENT_TYPE_LABELS.get(doc.document_type, doc.document_type),
            'generated_content': doc.generated_content,
            'fields': fields,
            'version': doc.version,
            'file_size': doc.format_size(),
            'is_locked': doc.is_locked,
            'lock_hint': doc.lock_hint,
            'is_final': doc.is_final,
            'signature_asset_id': str(doc.signature_asset_id) if doc.signature_asset_id else '',
            'encrypt_export': doc.encrypt_export,
            'download_url': f"/api/documents/{doc.id}/download/?pin={pin}&decrypted=1",
            'pdf_download_url': f"/api/documents/{doc.id}/pdf/?pin={pin}&decrypted=1",
            'encrypted_download_url': f"/api/documents/{doc.id}/download/?pin={pin}&passcode={pin}",
            'encrypted_pdf_download_url': f"/api/documents/{doc.id}/pdf/?pin={pin}&passcode={pin}",
        }
    })


@login_required
@require_GET
def get_document_detail_api(request, document_id):
    """Retrieve document details; checks lock status."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)

    is_session_unlocked = request.session.get(f'unlocked_doc_{doc.id}', False)
    pin_attempt = request.GET.get('pin') or ''
    if pin_attempt and doc.check_lock_pin(pin_attempt):
        is_session_unlocked = True
        request.session[f'unlocked_doc_{doc.id}'] = True

    # Locked documents require PIN authentication when accessed from history
    if doc.is_locked and not is_session_unlocked:
        return JsonResponse({
            'status': 'locked',
            'document_id': str(doc.id),
            'title': doc.title,
            'doc_type': doc.document_type,
            'is_locked': True,
            'lock_hint': doc.lock_hint,
            'file_size': doc.format_size(),
        })

    try:
        fields = json.loads(doc.fields_json) if doc.fields_json else {}
    except Exception:
        fields = {}

    return JsonResponse({
        'status': 'ok',
        'document': {
            'document_id': str(doc.id),
            'title': doc.title,
            'doc_type': doc.document_type,
            'doc_type_label': DOCUMENT_TYPE_LABELS.get(doc.document_type, doc.document_type),
            'generated_content': doc.generated_content,
            'fields': fields,
            'version': doc.version,
            'file_size': doc.format_size(),
            'is_locked': doc.is_locked,
            'lock_hint': doc.lock_hint,
            'is_final': doc.is_final,
            'signature_asset_id': str(doc.signature_asset_id) if doc.signature_asset_id else '',
            'encrypt_export': doc.encrypt_export,
            'download_url': f"/api/documents/{doc.id}/download/",
            'pdf_download_url': f"/api/documents/{doc.id}/pdf/",
        }
    })


@login_required
@require_GET
def list_user_documents_api(request):
    """List documents generated by the user (0 LLM calls)."""
    docs = GeneratedDocument.objects.filter(user=request.user)[:30]
    results = []
    for d in docs:
        results.append({
            'id': str(d.id),
            'title': d.title,
            'doc_type': d.document_type,
            'label': DOCUMENT_TYPE_LABELS.get(d.document_type, d.document_type),
            'version': d.version,
            'file_size': d.format_size(),
            'model_used': d.model_used,
            'is_locked': d.is_locked,
            'lock_hint': d.lock_hint,
            'is_final': d.is_final,
            'encrypt_export': d.encrypt_export,
            'created_at': d.created_at.strftime('%d %b %Y %H:%M'),
            'download_url': f"/api/documents/{d.id}/download/",
            'pdf_download_url': f"/api/documents/{d.id}/pdf/",
        })
    return JsonResponse({'documents': results})


@login_required
@require_POST
def update_profile_api(request):
    """Update officer profile credentials and digital signature preferences."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    user = request.user
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    user_updated = False
    if 'first_name' in data:
        user.first_name = first_name
        user_updated = True
    if 'last_name' in data:
        user.last_name = last_name
        user_updated = True
    if user_updated:
        user.save(update_fields=['first_name', 'last_name'])

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if 'employee_id' in data:
        profile.employee_id = str(data['employee_id']).strip()
    if 'department' in data:
        profile.department = str(data['department']).strip() or 'Combat Engineering Wing'
    if 'rank' in data:
        profile.rank = str(data['rank']).strip()
    if 'appointment' in data:
        profile.appointment = str(data['appointment']).strip()
    if 'authority' in data:
        profile.authority = str(data['authority']).strip()
    if 'signature_style' in data:
        profile.signature_style = str(data['signature_style']).strip() or 'military'
    if 'signature_text' in data:
        profile.signature_text = str(data['signature_text']).strip()

    profile.save()

    display_name = f"{user.first_name} {user.last_name}".strip() or user.username

    return JsonResponse({
        'status': 'ok',
        'profile': {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'display_name': display_name,
            'employee_id': profile.employee_id,
            'department': profile.department,
            'rank': profile.rank,
            'appointment': profile.appointment,
            'authority': profile.authority,
            'signature_style': profile.signature_style,
            'signature_text': profile.signature_text,
        }
    })


# ==============================================================================
# Signature Asset Management & Document Finalization APIs
# ==============================================================================

@login_required
@require_POST
def upload_signature_api(request):
    """Upload a signature image for the officer profile."""
    image_file = request.FILES.get('signature_image')
    if not image_file:
        return JsonResponse({'error': 'No image file provided'}, status=400)

    allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
    if image_file.content_type not in allowed_types:
        return JsonResponse({'error': 'Only PNG and JPG files are supported'}, status=400)

    if image_file.size > 2 * 1024 * 1024:
        return JsonResponse({'error': 'Signature image must be under 2 MB'}, status=400)

    # Validate image bytes and format integrity using Pillow (Air-Gap Defense Security)
    try:
        from PIL import Image
        with Image.open(image_file) as img:
            img.verify()
            fmt = (img.format or '').upper()
            if fmt not in ('PNG', 'JPEG', 'JPG'):
                return JsonResponse({'error': f'Image format {fmt} not supported. Use PNG or JPG.'}, status=400)
        image_file.seek(0)
    except Exception:
        return JsonResponse({'error': 'Invalid or corrupted image file structure'}, status=400)

    from .models import SignatureAsset
    label = request.POST.get('label', 'My Signature').strip() or 'My Signature'
    is_default = request.POST.get('is_default', 'false').lower() in ('true', '1')

    # If first signature, auto set as default
    if not SignatureAsset.objects.filter(user=request.user).exists():
        is_default = True

    sig = SignatureAsset.objects.create(
        user=request.user,
        label=label,
        image=image_file,
        is_default=is_default,
    )

    return JsonResponse({
        'status': 'ok',
        'signature': {
            'id': str(sig.id),
            'label': sig.label,
            'is_default': sig.is_default,
            'url': sig.image.url,
            'uploaded_at': sig.uploaded_at.strftime('%d %b %Y'),
        }
    })


@login_required
@require_GET
def list_signatures_api(request):
    """List all signature assets for the current user."""
    from .models import SignatureAsset
    sigs = SignatureAsset.objects.filter(user=request.user)
    return JsonResponse({
        'signatures': [
            {
                'id': str(s.id),
                'label': s.label,
                'is_default': s.is_default,
                'url': s.image.url,
                'uploaded_at': s.uploaded_at.strftime('%d %b %Y'),
            }
            for s in sigs
        ]
    })


@login_required
@require_POST
def delete_signature_api(request, signature_id):
    """Delete a signature asset."""
    from .models import SignatureAsset
    sig = get_object_or_404(SignatureAsset, id=signature_id, user=request.user)
    if sig.image and os.path.exists(sig.image.path):
        try:
            os.remove(sig.image.path)
        except Exception:
            pass
    sig.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def set_default_signature_api(request, signature_id):
    """Set a signature asset as the user's default."""
    from .models import SignatureAsset
    sig = get_object_or_404(SignatureAsset, id=signature_id, user=request.user)
    SignatureAsset.objects.filter(user=request.user, is_default=True).update(is_default=False)
    sig.is_default = True
    sig.save(update_fields=['is_default'])
    return JsonResponse({'status': 'ok', 'id': str(sig.id)})


@login_required
@require_POST
def toggle_document_final_api(request, document_id):
    """Toggle draft vs finalized status for a document."""
    doc = get_object_or_404(GeneratedDocument, id=document_id, user=request.user)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    if 'is_final' in data:
        doc.is_final = bool(data['is_final'])
    else:
        doc.is_final = not doc.is_final

    doc.save(update_fields=['is_final'])
    return JsonResponse({
        'status': 'ok',
        'document_id': str(doc.id),
        'is_final': doc.is_final,
        'message': 'Document marked as FINAL (DRAFT watermark removed).' if doc.is_final else 'Document marked as DRAFT.'
    })
