"""
Office Memo / Circular Template — CME Pune Standard.
Structure:
1. Top Classification Stamp
2. Header: CME Pune + OFFICE MEMORANDUM
3. Metadata Rows: TO, FROM, REF NO, DATE, SUBJECT
4. Body Paragraphs (LLM-generated / edited)
5. Action Required (optional)
6. Issuing Authority Signature Block
7. Bottom Classification Stamp
"""

import re
from docx.shared import Pt
from ..styles import (
    FONT_NAME, FONT_NAME_BODY, FONT_SIZE_BODY, FONT_SIZE_SMALL,
    COLOR_BLACK, ALIGN_LEFT, ALIGN_CENTER,
)
from .base_template import (
    create_base_document,
    add_text,
    add_classification_stamp,
    add_header_block,
    add_metadata_key_values,
    add_body_content,
    add_authority_signature_block,
)


def clean_subject(raw_subject):
    if not raw_subject:
        return 'OFFICIAL MATTER'
    s = re.sub(r'(?i)\bkey\s+points\s*:?', '', raw_subject)
    s = re.sub(r'(?i)^subject\s*:?', '', s)
    s = s.strip(' \t\n\r:;,-')
    return s.upper() or 'OFFICIAL MATTER'


def build_office_memo(fields, body_content):
    """Build an Office Memo / Circular DOCX."""
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    ref_no = fields.get('reference_number') or 'CME/MEMO/2026/001'
    date_str = fields.get('date') or ''
    to_val = fields.get('to') or fields.get('to_name') or 'All Concerned Officers & Branches'
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'Headquarters'
    signature_style = fields.get('signature_style', 'military')
    subject = clean_subject(fields.get('subject') or '')
    action_required = (fields.get('action_required') or '').strip()

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header
    add_header_block(doc, sub_title="OFFICE MEMORANDUM")

    # 3. Metadata Table
    metadata = [
        ('TO', to_val),
        ('FROM', f"{from_name} ({from_dept})"),
        ('REF NO', ref_no),
        ('DATE', date_str),
        ('SUBJECT', subject),
    ]
    add_metadata_key_values(doc, metadata)

    # 4. Body Content
    add_body_content(doc, body_content)

    # 5. Action Required (if provided)
    if action_required:
        p_act = doc.add_paragraph()
        p_act.paragraph_format.space_before = Pt(10)
        p_act.paragraph_format.space_after = Pt(6)
        r_lbl = p_act.add_run("ACTION REQUIRED: ")
        r_lbl.font.name = FONT_NAME
        r_lbl.font.size = Pt(9.5)
        r_lbl.font.bold = True
        r_val = p_act.add_run(action_required)
        r_val.font.name = FONT_NAME
        r_val.font.size = Pt(9.5)
        r_val.font.italic = True

    # 6. Signature Block
    add_authority_signature_block(
        doc,
        from_name=from_name,
        designation="Issuing Authority",
        dept=from_dept,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        date_str=date_str,
        signature_style=signature_style, signature_image_path=fields.get('_signature_image_path')
    )

    # 7. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc
