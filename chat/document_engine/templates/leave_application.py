"""
Leave Application Template — CME Pune Standard.
Complies with Indian Army Staff Duties format for leave applications.
"""

import re
from docx.shared import Pt
from ..styles import (
    FONT_NAME, FONT_NAME_BODY, FONT_SIZE_BODY,
    ALIGN_LEFT,
)
from .base_template import (
    create_base_document,
    add_classification_stamp,
    add_header_block,
    add_military_meta_table,
    add_body_content,
    add_military_signature_block,
)


def clean_subject(raw_subject):
    """Sanitize subject string."""
    if not raw_subject:
        return 'APPLICATION FOR LEAVE'
    s = re.sub(r'(?i)\bkey\s+points\s*:?', '', raw_subject)
    s = re.sub(r'(?i)^subject\s*:?', '', s)
    s = s.strip(' \t\n\r:;,-')
    return s.upper() or 'APPLICATION FOR LEAVE'


def build_leave_application(fields, body_content):
    """
    Build a Leave Application DOCX strictly matching CME Pune and Army regulations.
    """
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'RESTRICTED'
    ref_no = fields.get('reference_number') or 'CME/LEAVE/2026/0001'
    date_str = fields.get('date') or ''
    to_name = fields.get('to_name') or 'The Commandant,\nCollege of Military Engineering,\nDapodi, Pune – 411031'
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'Combat Engineering Wing'
    station = fields.get('station') or 'CME, Pune – 411031'
    signature_style = fields.get('signature_style') or 'military'
    signature_image_path = fields.get('_signature_image_path')

    leave_type = fields.get('leave_type') or 'CASUAL LEAVE'
    subject = fields.get('subject') or f"APPLICATION FOR {leave_type.upper()}"
    subject = clean_subject(subject)

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Header / Station Header
    add_header_block(doc)

    # 3. Military Metadata Table
    add_military_meta_table(doc, ref_no=ref_no, date_str=date_str, dept=from_dept, station=station)

    # 4. To Block
    p_to = doc.add_paragraph()
    p_to.paragraph_format.space_before = Pt(8)
    p_to.paragraph_format.space_after = Pt(2)
    p_to.paragraph_format.line_spacing = Pt(13)

    r_to_label = p_to.add_run("To,\n")
    r_to_label.font.name = FONT_NAME
    r_to_label.font.size = Pt(10)
    r_to_label.font.bold = True

    r_to_val = p_to.add_run(to_name)
    r_to_val.font.name = FONT_NAME
    r_to_val.font.size = Pt(10)

    # 5. Subject Line (Uppercase, Underlined, Bold)
    p_subj = doc.add_paragraph()
    p_subj.paragraph_format.space_before = Pt(10)
    p_subj.paragraph_format.space_after = Pt(10)

    r_sub_label = p_subj.add_run("SUBJECT: ")
    r_sub_label.font.name = FONT_NAME
    r_sub_label.font.size = Pt(10.5)
    r_sub_label.font.bold = True

    r_sub_val = p_subj.add_run(subject)
    r_sub_val.font.name = FONT_NAME
    r_sub_val.font.size = Pt(10.5)
    r_sub_val.font.bold = True
    r_sub_val.font.underline = True

    # 6. Salutation
    p_sal = doc.add_paragraph()
    p_sal.paragraph_format.space_before = Pt(0)
    p_sal.paragraph_format.space_after = Pt(8)
    r_sal = p_sal.add_run("Sir,")
    r_sal.font.name = FONT_NAME_BODY
    r_sal.font.size = FONT_SIZE_BODY

    # 7. Body Paragraphs
    add_body_content(doc, body_content)

    # 8. Signature Block
    add_military_signature_block(
        doc,
        from_name=from_name,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        dept=from_dept,
        encl='Medical Certificate / Supporting Documents (if applicable)',
        cc=f"Head of Department ({from_dept})",
        date_str=date_str,
        signature_style=signature_style,
        signature_image_path=signature_image_path,
    )

    # 9. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc
