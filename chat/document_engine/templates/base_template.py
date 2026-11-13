import os
"""
Base template — shared DOCX building logic adhering strictly to Indian Army CME standards.
Provides identical typography, classification headers, metadata blocks, and signatures.
"""

import re
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml

from ..styles import (
    PAGE_MARGIN_TOP, PAGE_MARGIN_BOTTOM, PAGE_MARGIN_LEFT, PAGE_MARGIN_RIGHT,
    FONT_NAME, FONT_NAME_BODY, FONT_SIZE_BODY, FONT_SIZE_HEADING, FONT_SIZE_SMALL,
    FONT_SIZE_META, FONT_SIZE_TITLE,
    COLOR_CONFIDENTIAL, COLOR_SECRET, COLOR_RESTRICTED, COLOR_UNCLASSIFIED,
    COLOR_BLACK, COLOR_DARK_GRAY, COLOR_MUTED,
    ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT, ALIGN_JUSTIFY,
    PARAGRAPH_SPACING_AFTER,
)


def get_classification_color(classification):
    """Return RGBColor corresponding to the security classification."""
    cls_upper = str(classification or 'CONFIDENTIAL').strip().upper()
    if 'SECRET' in cls_upper:
        return COLOR_SECRET
    elif 'RESTRICTED' in cls_upper:
        return COLOR_RESTRICTED
    elif 'UNCLASSIFIED' in cls_upper:
        return COLOR_UNCLASSIFIED
    return COLOR_CONFIDENTIAL


def create_base_document():
    """Create a new Document with standard military page setup and margins."""
    doc = Document()
    for section in doc.sections:
        section.top_margin = PAGE_MARGIN_TOP
        section.bottom_margin = PAGE_MARGIN_BOTTOM
        section.left_margin = PAGE_MARGIN_LEFT
        section.right_margin = PAGE_MARGIN_RIGHT
    return doc


def add_text(doc, text, font_size=FONT_SIZE_BODY, bold=False, italic=False,
             alignment=ALIGN_LEFT, space_before=Pt(0), space_after=PARAGRAPH_SPACING_AFTER,
             font_name=FONT_NAME, color=COLOR_BLACK, underline=False):
    """Add a paragraph with consistent military styling."""
    para = doc.add_paragraph()
    para.alignment = alignment
    para.paragraph_format.space_before = space_before
    para.paragraph_format.space_after = space_after

    run = para.add_run(text)
    run.font.name = font_name
    run.font.size = font_size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.underline = underline

    return para


def add_horizontal_line(doc):
    """Add a crisp 1.5pt solid horizontal divider line across the page."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    pPr = p._element.get_or_add_pPr()
    pBdr = parse_xml(
        r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        r'<w:bottom w:val="single" w:sz="12" w:space="1" w:color="0F172A"/>'
        r'</w:pBdr>'
    )
    pPr.append(pBdr)
    return p


def add_classification_stamp(doc, classification, is_top=True):
    """Add centered bold classification stamp (CONFIDENTIAL / RESTRICTED / SECRET / UNCLASSIFIED / NONE)."""
    if not classification:
        return None
    cls_text = str(classification).strip().upper()
    if cls_text in ('NONE', 'NOTHING', '', 'NO CLASSIFICATION'):
        return None
    color = get_classification_color(cls_text)

    p = doc.add_paragraph()
    p.alignment = ALIGN_CENTER
    if is_top:
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
    else:
        p.paragraph_format.space_before = Pt(26)
        p.paragraph_format.space_after = Pt(0)

    run = p.add_run(cls_text)
    run.font.name = FONT_NAME
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = color
    return p


def add_header_block(doc, sub_title=None, organization=None, sub_header=None):
    """Add official military stationery header with horizontal divider."""
    org_text = (organization or "COLLEGE OF MILITARY ENGINEERING").strip().upper()
    sub_text = (sub_header or "Dapodi, Pune - 411031 | Corps of Engineers").strip()

    # Line 1: Organization Name
    p_org = doc.add_paragraph()
    p_org.alignment = ALIGN_CENTER
    p_org.paragraph_format.space_before = Pt(0)
    p_org.paragraph_format.space_after = Pt(2)
    r_org = p_org.add_run(org_text)
    r_org.font.name = FONT_NAME
    r_org.font.size = FONT_SIZE_TITLE
    r_org.font.bold = True
    r_org.font.color.rgb = COLOR_BLACK

    # Line 2: Station & Corps Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = ALIGN_CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(4)
    r_sub = p_sub.add_run(sub_text)
    r_sub.font.name = FONT_NAME
    r_sub.font.size = Pt(9.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = COLOR_MUTED

    # Optional Archetype Title (e.g. OFFICE MEMORANDUM, MINUTES OF MEETING)
    if sub_title:
        p_archetype = doc.add_paragraph()
        p_archetype.alignment = ALIGN_CENTER
        p_archetype.paragraph_format.space_before = Pt(4)
        p_archetype.paragraph_format.space_after = Pt(4)
        r_arch = p_archetype.add_run(sub_title.upper())
        r_arch.font.name = FONT_NAME
        r_arch.font.size = Pt(12.5)
        r_arch.font.bold = True
        r_arch.font.color.rgb = COLOR_BLACK

    add_horizontal_line(doc)


def add_military_meta_table(doc, ref_no, date_str, dept=None, station=None):
    """
    Add standard military 2-column metadata table:
    Left: Tele and Reference Number
    Right: Branch, Station, and Date
    """
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell_l = table.cell(0, 0)
    cell_r = table.cell(0, 1)
    cell_l.width = Inches(3.2)
    cell_r.width = Inches(3.2)

    # Left Cell
    p_l = cell_l.paragraphs[0]
    p_l.alignment = ALIGN_LEFT
    p_l.paragraph_format.space_after = Pt(2)
    p_l.paragraph_format.line_spacing = Pt(13)
    
    r1 = p_l.add_run("Tele: 020-27146000/2204\n")
    r1.font.name = FONT_NAME
    r1.font.size = FONT_SIZE_META
    r1.font.color.rgb = COLOR_DARK_GRAY

    r2 = p_l.add_run(f"Ref: {ref_no or 'CME/GEN/2026/0001'}")
    r2.font.name = FONT_NAME
    r2.font.size = FONT_SIZE_META
    r2.font.bold = True
    r2.font.color.rgb = COLOR_BLACK

    # Right Cell
    p_r = cell_r.paragraphs[0]
    p_r.alignment = ALIGN_RIGHT
    p_r.paragraph_format.space_after = Pt(2)
    p_r.paragraph_format.line_spacing = Pt(13)

    dept_text = dept or 'Combat Engineering Wing'
    station_text = station or 'CME, Pune - 411031'
    r3 = p_r.add_run(f"{dept_text}\n{station_text}\n")
    r3.font.name = FONT_NAME
    r3.font.size = FONT_SIZE_META
    r3.font.color.rgb = COLOR_DARK_GRAY

    r4 = p_r.add_run(str(date_str or ''))
    r4.font.name = FONT_NAME
    r4.font.size = FONT_SIZE_META
    r4.font.bold = True
    r4.font.color.rgb = COLOR_BLACK

    return table


def add_metadata_key_values(doc, kv_list):
    """
    Add key-value metadata rows (for Memos, Orders, Notes, MoM):
    kv_list is a list of tuples: [('TO', val), ('FROM', val), ...]
    """
    for key, val in kv_list:
        if val is None or str(val).strip() == '':
            continue
        p = doc.add_paragraph()
        p.alignment = ALIGN_LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)

        r_key = p.add_run(f"{str(key).upper()}: ")
        r_key.font.name = FONT_NAME
        r_key.font.size = FONT_SIZE_META
        r_key.font.bold = True
        r_key.font.color.rgb = COLOR_BLACK

        r_val = p.add_run(str(val))
        r_val.font.name = FONT_NAME
        r_val.font.size = FONT_SIZE_META
        r_val.font.color.rgb = COLOR_BLACK

    add_horizontal_line(doc)


def add_body_content(doc, content):
    """Add the body content as properly formatted justified paragraphs."""
    paragraphs = (content or '').strip().split('\n')
    for para_text in paragraphs:
        para_text = para_text.strip()
        if not para_text:
            continue
        p = doc.add_paragraph()
        p.alignment = ALIGN_JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = Pt(15)

        run = p.add_run(para_text)
        run.font.name = FONT_NAME_BODY
        run.font.size = FONT_SIZE_BODY
        run.font.color.rgb = COLOR_BLACK


def add_military_signature_block(doc, from_name='', from_rank='', from_appointment='', from_authority='', dept='Combat Engineering Wing', encl='', cc=None, date_str='', signature_style='military', signature_image_path=None):
    """
    Add military-standard 2-column footer block:
    Left: Enclosures and Copy-To routing
    Right: Clean Military Staff Duties Signature or e-Office DSC certificate block
    """
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell_l = table.cell(0, 0)
    cell_r = table.cell(0, 1)
    cell_l.width = Inches(3.2)
    cell_r.width = Inches(3.2)

    # Left cell: Enclosures & CC
    p_l = cell_l.paragraphs[0]
    p_l.alignment = ALIGN_LEFT
    p_l.paragraph_format.space_before = Pt(20)
    p_l.paragraph_format.space_after = Pt(2)

    if encl and str(encl).strip() and str(encl).strip().lower() not in ('none', 'as stated'):
        r_encl = p_l.add_run(f"Encl: {encl}\n")
        r_encl.font.name = FONT_NAME
        r_encl.font.size = Pt(9.5)
        r_encl.font.bold = True
        r_encl.font.color.rgb = COLOR_BLACK
    elif encl and str(encl).strip():
        r_encl = p_l.add_run(f"Encl: {encl}\n")
        r_encl.font.name = FONT_NAME
        r_encl.font.size = Pt(9.5)
        r_encl.font.bold = True
        r_encl.font.color.rgb = COLOR_BLACK

    if cc and str(cc).strip():
        r_cc = p_l.add_run(f"Copy to: {cc}")
        r_cc.font.name = FONT_NAME
        r_cc.font.size = FONT_SIZE_SMALL
        r_cc.font.color.rgb = COLOR_MUTED

    # Right cell
    p_r = cell_r.paragraphs[0]
    p_r.alignment = ALIGN_RIGHT
    p_r.paragraph_format.space_before = Pt(20)
    p_r.paragraph_format.space_after = Pt(2)
    p_r.paragraph_format.line_spacing = Pt(13)

    if signature_style == 'eoffice':
        # Formal Government e-Office DSC Certificate frame
        r_cert = p_r.add_run("[DIGITALLY SIGNED CERTIFICATE (DSC)]\n")
        r_cert.font.name = FONT_NAME
        r_cert.font.size = Pt(8)
        r_cert.font.bold = True
        r_cert.font.color.rgb = RGBColor(15, 23, 42)

        signer_name = str(from_name).strip() or 'Issuing Officer'
        r_sig = p_r.add_run(f"Signed by: ({signer_name})\n")
        r_sig.font.name = FONT_NAME
        r_sig.font.size = Pt(9.5)
        r_sig.font.bold = True

        role_parts = [p.strip() for p in [from_rank, from_appointment] if p and str(p).strip()]
        if role_parts:
            r_role = p_r.add_run(f"Designation: {', '.join(role_parts)}\n")
            r_role.font.name = FONT_NAME
            r_role.font.size = Pt(8.5)

        if from_authority and str(from_authority).strip():
            auth_text = str(from_authority).strip()
            if not auth_text.lower().startswith('for '):
                auth_text = f"for {auth_text}"
            r_for = p_r.add_run(f"Authority: {auth_text}\n")
            r_for.font.name = FONT_NAME
            r_for.font.size = Pt(8.5)

        r_tok = p_r.add_run(f"Date: {date_str or 'Today'} IST | Air-Gap PKI Verified")
        r_tok.font.name = FONT_NAME
        r_tok.font.size = Pt(7.5)
        r_tok.font.italic = True
        r_tok.font.color.rgb = COLOR_MUTED
    else:
        # Standard Authentic Military Staff Duties Format (No cartoon badges)
        if signature_image_path and os.path.exists(signature_image_path):
            try:
                r_img = p_r.add_run()
                r_img.add_picture(signature_image_path, height=Inches(0.45))
                p_r.add_run("\n")
            except Exception:
                pass
        signer_name = str(from_name).strip() or 'Issuing Officer'
        r_sig = p_r.add_run(f"({signer_name})\n")
        r_sig.font.name = FONT_NAME
        r_sig.font.size = Pt(10)
        r_sig.font.bold = True
        r_sig.font.color.rgb = COLOR_BLACK

        role_parts = [p.strip() for p in [from_rank, from_appointment] if p and str(p).strip()]
        if role_parts:
            r_role = p_r.add_run(", ".join(role_parts) + "\n")
            r_role.font.name = FONT_NAME
            r_role.font.size = Pt(9.5)
            r_role.font.color.rgb = COLOR_BLACK

        if from_authority and str(from_authority).strip():
            auth_text = str(from_authority).strip()
            if not auth_text.lower().startswith('for '):
                auth_text = f"for {auth_text}"
            r_for = p_r.add_run(f"{auth_text}\n")
            r_for.font.name = FONT_NAME
            r_for.font.size = Pt(8.5)
            r_for.font.color.rgb = COLOR_MUTED

    return table


def add_authority_signature_block(doc, from_name='', designation='Issuing Authority', dept='', from_rank='', from_appointment='', from_authority='', date_str='', signature_style='military', signature_image_path=None):
    """Add professional right-aligned military signature block (classic Staff Duties or e-Office DSC)."""
    p = doc.add_paragraph()
    p.alignment = ALIGN_RIGHT
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(2)

    signer_name = str(from_name).strip() if from_name else 'Issuing Officer'

    role_parts = [p.strip() for p in [from_rank, from_appointment] if p and str(p).strip()]
    if not role_parts and designation and designation not in ('Issuing Authority', 'Submitted for Approval', 'By Order'):
        role_parts = [designation.strip()]

    if signature_style == 'eoffice':
        r_cert = p.add_run("[DIGITALLY SIGNED CERTIFICATE (DSC)]\n")
        r_cert.font.name = FONT_NAME
        r_cert.font.size = Pt(8.5)
        r_cert.font.bold = True
        r_cert.font.color.rgb = RGBColor(15, 23, 42)

        r_name = p.add_run(f"Signed by: ({signer_name})\n")
        r_name.font.name = FONT_NAME
        r_name.font.size = Pt(9.5)
        r_name.font.bold = True
        r_name.font.color.rgb = COLOR_BLACK

        if role_parts:
            r_desig = p.add_run("Designation: " + ", ".join(role_parts) + "\n")
            r_desig.font.name = FONT_NAME
            r_desig.font.size = Pt(8.5)
            r_desig.font.color.rgb = COLOR_BLACK

        if from_authority and str(from_authority).strip():
            auth_text = str(from_authority).strip()
            if not auth_text.lower().startswith('for '):
                auth_text = f"for {auth_text}"
            r_auth = p.add_run(f"Authority: {auth_text}\n")
            r_auth.font.name = FONT_NAME
            r_auth.font.size = Pt(8.5)
            r_auth.font.color.rgb = COLOR_MUTED

        r_tok = p.add_run(f"Date: {date_str or 'Today'} IST | Air-Gap PKI Verified")
        r_tok.font.name = FONT_NAME
        r_tok.font.size = Pt(7.5)
        r_tok.font.italic = True
        r_tok.font.color.rgb = COLOR_MUTED
    else:
        # Classic Military Staff Duties Standard
        if signature_image_path and os.path.exists(signature_image_path):
            try:
                r_img = p.add_run()
                r_img.add_picture(signature_image_path, height=Inches(0.45))
                p.add_run("\n")
            except Exception:
                pass
        r_name = p.add_run(f"({signer_name})\n")
        r_name.font.name = FONT_NAME
        r_name.font.size = Pt(10)
        r_name.font.bold = True
        r_name.font.color.rgb = COLOR_BLACK

        if role_parts:
            r_desig = p.add_run(", ".join(role_parts) + "\n")
            r_desig.font.name = FONT_NAME
            r_desig.font.size = Pt(9.5)
            r_desig.font.color.rgb = COLOR_BLACK

        if from_authority and str(from_authority).strip():
            auth_text = str(from_authority).strip()
            if not auth_text.lower().startswith('for '):
                auth_text = f"for {auth_text}"
            r_auth = p.add_run(f"{auth_text}\n")
            r_auth.font.name = FONT_NAME
            r_auth.font.size = Pt(8.5)
            r_auth.font.color.rgb = COLOR_MUTED
        elif dept and str(dept).strip():
            r_dept = p.add_run(f"{dept}\n")
            r_dept.font.name = FONT_NAME
            r_dept.font.size = Pt(8.5)
            r_dept.font.color.rgb = COLOR_MUTED
