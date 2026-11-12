"""
Meeting Minutes (MoM) Template — CME Pune Standard.
Structure:
1. Top Classification Stamp
2. Header: CME Pune + MINUTES OF MEETING: {TITLE}
3. Metadata Rows: DATE & TIME, VENUE, CHAIRPERSON, ATTENDEES
4. Proceedings & Discussions (LLM-generated / edited)
5. Action Items & Deliverables (optional)
6. Next Meeting Schedule (optional)
7. Prepared By Signature
8. Bottom Classification Stamp
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


def build_meeting_minutes(fields, body_content):
    """Build a Meeting Minutes (MoM) DOCX."""
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    title = (fields.get('meeting_title') or fields.get('title') or 'CONFERENCE & COORD MEETING').upper()
    date_str = fields.get('date') or ''
    venue = fields.get('venue') or 'Conference Hall, CME'
    chairperson = fields.get('chairperson') or 'Commandant CME'
    attendees = fields.get('attendees') or 'All Wing Heads and Branch Representatives'
    action_items = (fields.get('action_items') or '').strip()
    next_meeting = (fields.get('next_meeting') or '').strip()
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'Coordination Wing'
    signature_style = fields.get('signature_style', 'military')

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header
    add_header_block(doc, sub_title=f"MINUTES OF MEETING: {title}")

    # 3. Details Table
    details = [
        ('DATE & TIME', date_str),
        ('VENUE', venue),
        ('CHAIRPERSON', chairperson),
        ('ATTENDEES', attendees),
    ]
    add_metadata_key_values(doc, details)

    # 4. Heading: Record of Proceedings
    p_rec = doc.add_paragraph()
    p_rec.paragraph_format.space_before = Pt(4)
    p_rec.paragraph_format.space_after = Pt(8)
    r_rec = p_rec.add_run("RECORD OF PROCEEDINGS & DELIBERATIONS:")
    r_rec.font.name = FONT_NAME
    r_rec.font.size = Pt(10.5)
    r_rec.font.bold = True
    r_rec.font.underline = True

    # 5. Body Content
    add_body_content(doc, body_content)

    # 6. Action Items (if provided)
    if action_items:
        p_act_h = doc.add_paragraph()
        p_act_h.paragraph_format.space_before = Pt(12)
        p_act_h.paragraph_format.space_after = Pt(4)
        r_ah = p_act_h.add_run("ACTION ITEMS & DELIVERABLES:")
        r_ah.font.name = FONT_NAME
        r_ah.font.size = Pt(10)
        r_ah.font.bold = True
        r_ah.font.underline = True

        for line in action_items.split('\n'):
            line = line.strip()
            if line:
                p_it = doc.add_paragraph()
                p_it.paragraph_format.left_indent = Pt(14)
                p_it.paragraph_format.space_before = Pt(0)
                p_it.paragraph_format.space_after = Pt(3)
                r_it = p_it.add_run(f"• {line}")
                r_it.font.name = FONT_NAME
                r_it.font.size = Pt(9.5)

    # 7. Next Meeting (if provided)
    if next_meeting:
        p_nm = doc.add_paragraph()
        p_nm.paragraph_format.space_before = Pt(10)
        p_nm.paragraph_format.space_after = Pt(4)
        r_nm = p_nm.add_run(f"Next Meeting Scheduled: {next_meeting}")
        r_nm.font.name = FONT_NAME
        r_nm.font.size = Pt(9.5)
        r_nm.font.italic = True

    # 8. Signature Block
    add_authority_signature_block(
        doc,
        from_name=from_name,
        designation="Recorded and Circulated by",
        dept=from_dept,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        date_str=date_str,
        signature_style=signature_style
    )

    # 9. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc
