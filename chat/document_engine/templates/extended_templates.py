"""
Office Note, Office Order, and Technical Report templates — Doctrinal CME Pune Standard.
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


def build_office_note(fields, body_content):
    """Build an Office Note / Note Sheet DOCX."""
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    ref_no = fields.get('reference_number') or 'CME/NOTE/2026/001'
    date_str = fields.get('date') or ''
    subject = clean_subject(fields.get('subject') or '')
    references = (fields.get('references') or '').strip()
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'General Staff Branch'
    signature_style = fields.get('signature_style', 'military')

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header
    add_header_block(doc, sub_title="OFFICE NOTE / NOTE SHEET")

    # 3. Metadata Rows
    metadata = [
        ('FILE / REF NO', ref_no),
        ('DATE', date_str),
        ('SUBJECT', subject),
    ]
    if references:
        metadata.append(('REFERENCES', references))
    add_metadata_key_values(doc, metadata)

    # 4. Body Content
    add_body_content(doc, body_content)

    # 5. Signature Block
    add_authority_signature_block(
        doc,
        from_name=from_name,
        designation="Submitted for Approval",
        dept=from_dept,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        date_str=date_str,
        signature_style=signature_style
    )

    # 6. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc


def build_office_order(fields, body_content):
    """Build an Official Office Order DOCX."""
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    ref_no = fields.get('reference_number') or 'CME/ORDER/2026/001'
    date_str = fields.get('date') or ''
    subject = clean_subject(fields.get('subject') or '')
    authority = fields.get('authority') or 'Commandant CME'
    effective_date = (fields.get('effective_date') or '').strip()
    distribution = (fields.get('distribution') or '').strip()
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'General Staff Branch'
    signature_style = fields.get('signature_style', 'military')

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header
    add_header_block(doc, sub_title="OFFICE ORDER")

    # 3. Metadata Rows
    metadata = [
        ('ORDER NO', ref_no),
        ('DATE', date_str),
        ('SUBJECT', subject),
        ('AUTHORITY', authority),
    ]
    add_metadata_key_values(doc, metadata)

    # 4. Body Content
    add_body_content(doc, body_content)

    # 5. Effective Date
    if effective_date:
        p_eff = doc.add_paragraph()
        p_eff.paragraph_format.space_before = Pt(10)
        p_eff.paragraph_format.space_after = Pt(4)
        r_eff = p_eff.add_run(f"Effective Date: {effective_date}")
        r_eff.font.name = FONT_NAME
        r_eff.font.size = Pt(9.5)
        r_eff.font.italic = True

    # 6. Signature Block
    add_authority_signature_block(
        doc,
        from_name=from_name,
        designation="By Order",
        dept=from_dept,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        date_str=date_str,
        signature_style=signature_style
    )

    # 7. Distribution List (if provided)
    if distribution:
        p_dist_h = doc.add_paragraph()
        p_dist_h.paragraph_format.space_before = Pt(12)
        p_dist_h.paragraph_format.space_after = Pt(4)
        r_dh = p_dist_h.add_run("Distribution:")
        r_dh.font.name = FONT_NAME
        r_dh.font.size = Pt(9.5)
        r_dh.font.bold = True

        for item in distribution.split(','):
            item = item.strip()
            if item:
                p_di = doc.add_paragraph()
                p_di.paragraph_format.left_indent = Pt(14)
                p_di.paragraph_format.space_before = Pt(0)
                p_di.paragraph_format.space_after = Pt(2)
                r_di = p_di.add_run(f"• {item}")
                r_di.font.name = FONT_NAME
                r_di.font.size = Pt(9)

    # 8. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc


def build_technical_report(fields, body_content):
    """Build a Technical Report DOCX."""
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    title = (fields.get('title') or 'TECHNICAL & TRIAL EVALUATION REPORT').upper()
    ref_no = fields.get('reference_number') or 'CME/TR/2026/001'
    date_str = fields.get('date') or ''
    author = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    author_dept = fields.get('from_department') or 'Combat Engineering Trials Wing'
    signature_style = fields.get('signature_style', 'military')
    abstract = (fields.get('abstract') or '').strip()

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header
    add_header_block(doc, sub_title=title)

    # 3. Metadata Rows
    metadata = [
        ('REPORT ID', ref_no),
        ('DATE', date_str),
        ('AUTHOR', f"{author} ({author_dept})"),
    ]
    add_metadata_key_values(doc, metadata)

    # 4. Executive Summary (if provided)
    if abstract:
        p_abs_h = doc.add_paragraph()
        p_abs_h.paragraph_format.space_before = Pt(4)
        p_abs_h.paragraph_format.space_after = Pt(2)
        r_ah = p_abs_h.add_run("EXECUTIVE SUMMARY")
        r_ah.font.name = FONT_NAME
        r_ah.font.size = Pt(10)
        r_ah.font.bold = True
        r_ah.font.underline = True

        p_abs = doc.add_paragraph()
        p_abs.paragraph_format.space_before = Pt(0)
        p_abs.paragraph_format.space_after = Pt(10)
        r_abs = p_abs.add_run(abstract)
        r_abs.font.name = FONT_NAME
        r_abs.font.size = Pt(9.5)
        r_abs.font.italic = True

    # 5. Body Content
    add_body_content(doc, body_content)

    # 6. Signature Block
    add_authority_signature_block(
        doc,
        from_name=author,
        designation="Prepared and Submitted by",
        dept=author_dept,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        date_str=date_str,
        signature_style=signature_style
    )

    # 7. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc
