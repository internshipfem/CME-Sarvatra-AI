"""
Formal Letter Template — Doctrinal CME Pune Standard.
Structure:
1. Top Classification Stamp
2. CME Header & Divider
3. Tele / Ref (Left) and Branch / Station / Date (Right)
4. To Address Block
5. SUBJECT Line (Uppercase, Underlined, Bold)
6. Salutation (Sir,)
7. Body Paragraphs (LLM-generated, justified)
8. Military Signature Block & Enclosure / CC Routing
9. Bottom Classification Stamp
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
    add_military_meta_table,
    add_body_content,
    add_military_signature_block,
)


def clean_subject(raw_subject):
    """Sanitize subject string."""
    if not raw_subject:
        return 'OFFICIAL MATTER'
    s = re.sub(r'(?i)\bkey\s+points\s*:?', '', raw_subject)
    s = re.sub(r'(?i)^subject\s*:?', '', s)
    s = s.strip(' \t\n\r:;,-')
    return s.upper() or 'OFFICIAL MATTER'


def build_formal_letter(fields, body_content):
    """
    Build a Formal Military Letter DOCX strictly matching the Live Studio and PDF standards.
    """
    fields = fields or {}
    doc = create_base_document()

    classification = fields.get('classification') if fields.get('classification') is not None else 'NONE'
    ref_no = fields.get('reference_number') or 'CME/CEW/2026/0001'
    date_str = fields.get('date') or ''
    to_name = fields.get('to_name') or fields.get('to') or 'The Commandant,\nCollege of Military Engineering, Pune'
    subject = clean_subject(fields.get('subject') or '')
    from_name = fields.get('from_name') or ''
    from_rank = fields.get('from_rank') or ''
    from_appointment = fields.get('from_appointment') or ''
    from_authority = fields.get('from_authority') or ''
    from_dept = fields.get('from_department') or 'Combat Engineering Wing'
    station = fields.get('station') or 'CME, Pune - 411031'
    cc = fields.get('cc') or fields.get('cc_list') or ''
    enclosures = fields.get('enclosures') or 'As stated'
    salutation = fields.get('salutation') or 'Sir,'
    signature_style = fields.get('signature_style') or 'military'

    # 1. Top Classification Stamp
    add_classification_stamp(doc, classification, is_top=True)

    # 2. CME Letterhead / Station Header
    add_header_block(doc)

    # 3. Military Metadata Table (Tele / Ref on Left, Wing / Station / Date on Right)
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

    # 6. Salutation (Military Standard)
    p_sal = doc.add_paragraph()
    p_sal.paragraph_format.space_before = Pt(0)
    p_sal.paragraph_format.space_after = Pt(8)
    r_sal = p_sal.add_run(salutation)
    r_sal.font.name = FONT_NAME_BODY
    r_sal.font.size = FONT_SIZE_BODY

    # 7. Body Paragraphs (LLM-generated / edited)
    add_body_content(doc, body_content)

    # 8. Signature Block (Left: Encl & CC; Right: Officer details with Digital Signature Certificate)
    add_military_signature_block(
        doc,
        from_name=from_name,
        from_rank=from_rank,
        from_appointment=from_appointment,
        from_authority=from_authority,
        dept=from_dept,
        encl=enclosures,
        cc=cc,
        date_str=date_str,
        signature_style=signature_style
    )

    # 9. Bottom Classification Stamp
    add_classification_stamp(doc, classification, is_top=False)

    return doc
