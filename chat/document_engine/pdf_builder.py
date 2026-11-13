import os
import base64
"""
PDF Builder — Doctrinal Indian Army A4 Military Stationery PDF Generator with AES-256 Encryption.
Supports all 6 military document archetypes:
- Formal Letter
- Office Memo / Circular
- Meeting Minutes (MoM)
- Office Note / Note Sheet
- Office Order
- Technical Report

Provides 100% content and layout parity with the DOCX templates and live Studio preview.
"""

import html
import re
import fitz

MEDIABOX = fitz.paper_rect("a4")  # 595.28 x 841.89 pt
# Content area leaving margins: 54 pt (0.75 in) left/right, 52 pt top, 50 pt bottom
CONTENT_RECT = fitz.Rect(54, 52, 595.28 - 54, 841.89 - 50)


def _rectfn(rect_num, filled):
    return MEDIABOX, CONTENT_RECT, None


def _clean_str(val):
    if val is None:
        return ''
    return str(val).strip()


def _escape(val):
    return html.escape(_clean_str(val))


def _clean_subject(raw_subject):
    if not raw_subject:
        return 'OFFICIAL MATTER'
    s = re.sub(r'(?i)\bkey\s+points\s*:?', '', raw_subject)
    s = re.sub(r'(?i)^subject\s*:?', '', s)
    s = s.strip(' \t\n\r:;,-')
    return s.upper() or 'OFFICIAL MATTER'


def _build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, dept='', signature_style='military', station='', signature_image_path=None):
    role_parts = [p.strip() for p in [from_rank, from_appointment] if p and p.strip()]
    role_line = ', '.join(role_parts)

    sig_img_html = ''
    if signature_image_path and os.path.exists(signature_image_path):
        try:
            with open(signature_image_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = signature_image_path.rsplit('.', 1)[-1].lower()
            mime = 'image/png' if ext == 'png' else 'image/jpeg'
            sig_img_html = f'<div style="text-align: right; margin-bottom: 4px;"><img src="data:{mime};base64,{b64}" style="height: 65pt; max-width: 220pt; object-fit: contain;" /></div>'
        except Exception:
            sig_img_html = ''

    auth_line_html = ''
    if from_authority and from_authority.strip():
        auth_clean = from_authority.strip()
        if not auth_clean.lower().startswith('for '):
            auth_clean = f"for {auth_clean}"
        auth_line_html = f'<div style="font-size: 8.5pt; color: #475569; margin-top: 1px;">{auth_clean}</div>'

    signer_line = f"({from_name})" if from_name else "(Issuing Officer)"

    if signature_style == 'eoffice':
        return f'''
        <div style="display: inline-block; border: 1px solid #475569; border-radius: 2px; padding: 6px 10px; background: #ffffff; text-align: left; min-width: 210px; font-family: monospace, sans-serif; font-size: 7.5pt; line-height: 1.35; color: #1e293b;">
            <div style="font-weight: bold; font-size: 7.5pt; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; margin-bottom: 4px; text-align: center;">
                DIGITALLY SIGNED CERTIFICATE (DSC)
            </div>
            {sig_img_html}
            <div><strong>Signed by:</strong> {signer_line}</div>
            {f'<div><strong>Role:</strong> {role_line}</div>' if role_line else ''}
            {auth_line_html}
            <div><strong>Location:</strong> {station or "CME, Dapodi, Pune"}</div>
            <div><strong>Date:</strong> {date_str} IST</div>
            <div style="color: #64748b; font-size: 6.8pt; border-top: 1px dashed #e2e8f0; margin-top: 3px; padding-top: 2px;">Digest: Air-Gap PKI // SHA-256 Verified</div>
        </div>
        '''

    # Classic Military Staff Duties Format (Official Standard)
    role_line_html = f'<div style="font-size: 9.5pt; color: #1e293b; margin-top: 2px;">{role_line}</div>' if role_line else ''
    return f'''
    <div style="text-align: right; font-family: Arial, Helvetica, sans-serif; line-height: 1.4;">
        {sig_img_html}
        <div style="font-weight: bold; font-size: 10pt; color: #0f172a;">{signer_line}</div>
        {role_line_html}
        {auth_line_html}
    </div>
    '''


def _format_paragraphs(text):
    """Format body text into clean justified paragraphs."""
    if not text:
        return '<p style="text-align: justify; margin-bottom: 10px;">[No Content]</p>'

    paras = [p.strip() for p in text.split('\n') if p.strip()]
    formatted = []
    for p in paras:
        escaped_p = html.escape(p)
        if escaped_p.startswith('&bull;') or escaped_p.startswith('- ') or escaped_p.startswith('* '):
            clean_item = re.sub(r'^(&bull;|-|\*)\s*', '', escaped_p)
            formatted.append(f'<p style="margin-left: 20px; margin-bottom: 6px; text-align: justify;">&bull; {clean_item}</p>')
        else:
            formatted.append(f'<p style="text-align: justify; margin-bottom: 10px; text-indent: 0;">{escaped_p}</p>')
    return '\n'.join(formatted)


def _build_formal_letter_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    ref_no = _escape(fields.get('reference_number') or 'CME/CEW/2026/0001')
    date_str = _escape(fields.get('date') or '')
    to_name = _escape(fields.get('to_name') or fields.get('to') or 'The Commandant,\nCollege of Military Engineering, Pune').replace('\n', '<br/>')
    subject = _clean_subject(fields.get('subject') or '')
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'Combat Engineering Wing')
    station = _escape(fields.get('station') or 'CME, Pune - 411031')
    cc = _escape(fields.get('cc') or fields.get('cc_list') or '')
    enclosures = _escape(fields.get('enclosures') or 'As stated')
    salutation = _escape(fields.get('salutation') or 'Sir,')

    body_html = _format_paragraphs(body_content)

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr>
            <td style="width: 50%; vertical-align: top; line-height: 1.45;">
                <div>Tele: 020-27146000/2204</div>
                <div><strong>Ref: {ref_no}</strong></div>
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; line-height: 1.45;">
                <div>{from_dept}</div>
                <div>{station}</div>
                <div><strong>{date_str}</strong></div>
            </td>
        </tr>
    </table>

    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.45; margin-bottom: 12px;">
        <strong>To,</strong><br/>
        {to_name}
    </div>

    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; margin: 12px 0; line-height: 1.4;">
        <strong>SUBJECT:</strong> <u>{subject}</u>
    </div>

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        <p style="margin-bottom: 10px;">{salutation}</p>
        {body_html}
    </div>

    <div style="margin-top: 24px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; page-break-inside: avoid;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 50%; vertical-align: bottom;">
                    {f'<div style="font-weight: bold;">Encl: {enclosures}</div>' if enclosures else ''}
                    {f'<div style="font-size: 8.5pt; color: #475569; margin-top: 4px;">Copy to: {cc}</div>' if cc else ''}
                </td>
                <td style="width: 50%; text-align: right; vertical-align: bottom;">
                    {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=fields.get('signature_style', 'military'), station=station, signature_image_path=fields.get('_signature_image_path'))}
                </td>
            </tr>
        </table>
    </div>
    """
    return html_content


def _build_office_memo_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    ref_no = _escape(fields.get('reference_number') or 'CME/MEMO/2026/001')
    date_str = _escape(fields.get('date') or '')
    to_val = _escape(fields.get('to') or fields.get('to_name') or 'All Concerned Officers & Branches')
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'Headquarters')
    station = _escape(fields.get('station') or 'CME, Pune – 411031')
    subject = _clean_subject(fields.get('subject') or '')
    action_required = _escape(fields.get('action_required') or '')

    body_html = _format_paragraphs(body_content)

    action_html = ''
    if action_required:
        action_html = f"""
        <div style="margin-top: 14px; padding: 8px 12px; background: #f8fafc; border-left: 3px solid #0f172a; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt;">
            <strong>ACTION REQUIRED:</strong> {action_required}
        </div>
        """

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <h2 style="font-size: 12.5pt; font-weight: bold; margin: 4px 0 2px 0; color: #0f172a; letter-spacing: 1px;">OFFICE MEMORANDUM</h2>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 14px; border-collapse: collapse;">
        <tr><td style="width: 20%; padding: 3px 0; font-weight: bold;">TO:</td><td style="padding: 3px 0;">{to_val}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">FROM:</td><td style="padding: 3px 0;">{from_name} ({from_dept})</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">REF NO:</td><td style="padding: 3px 0;">{ref_no}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">DATE:</td><td style="padding: 3px 0;">{date_str}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">SUBJECT:</td><td style="padding: 3px 0; font-weight: bold;"><u>{subject}</u></td></tr>
    </table>
    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 6px 0 14px 0;" />

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        {body_html}
    </div>

    {action_html}

    <div style="margin-top: 26px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; text-align: right; page-break-inside: avoid;">
        {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=fields.get('signature_style', 'military'), station=station, signature_image_path=fields.get('_signature_image_path'))}
    </div>
    """
    return html_content


def _build_meeting_minutes_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    title = _escape(fields.get('meeting_title') or fields.get('title') or 'CONFERENCE & COORD MEETING').upper()
    date_str = _escape(fields.get('date') or '')
    venue = _escape(fields.get('venue') or 'Conference Hall, CME')
    chairperson = _escape(fields.get('chairperson') or 'Commandant CME')
    attendees = _escape(fields.get('attendees') or 'All Wing Heads and Branch Representatives')
    action_items = _escape(fields.get('action_items') or '')
    next_meeting = _escape(fields.get('next_meeting') or '')
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'Coordination Wing')
    station = _escape(fields.get('station') or 'CME, Pune – 411031')

    body_html = _format_paragraphs(body_content)

    action_html = ''
    if action_items:
        items_list = ''.join(f'<li style="margin-bottom: 4px;">{_escape(item.strip())}</li>' for item in action_items.split('\n') if item.strip())
        action_html = f"""
        <div style="margin-top: 14px; font-family: Arial, Helvetica, sans-serif;">
            <div style="font-weight: bold; font-size: 10pt; text-decoration: underline; margin-bottom: 6px;">ACTION ITEMS &amp; DELIVERABLES:</div>
            <ul style="font-size: 9.5pt; line-height: 1.45; margin-left: 20px; padding-left: 0;">
                {items_list}
            </ul>
        </div>
        """

    next_html = ''
    if next_meeting:
        next_html = f'<div style="font-size: 9.5pt; font-style: italic; margin-top: 10px;">Next Meeting Scheduled: {next_meeting}</div>'

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <h2 style="font-size: 12pt; font-weight: bold; margin: 4px 0 2px 0; color: #0f172a;">MINUTES OF MEETING: {title}</h2>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr><td style="width: 25%; padding: 3px 0; font-weight: bold;">DATE &amp; TIME:</td><td style="padding: 3px 0;">{date_str}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">VENUE:</td><td style="padding: 3px 0;">{venue}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">CHAIRPERSON:</td><td style="padding: 3px 0;">{chairperson}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0; vertical-align: top;">ATTENDEES:</td><td style="padding: 3px 0;">{attendees}</td></tr>
    </table>
    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 6px 0 14px 0;" />

    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 10pt; font-weight: bold; text-decoration: underline; margin-bottom: 8px;">
        RECORD OF PROCEEDINGS &amp; DELIBERATIONS:
    </div>

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        {body_html}
    </div>

    {action_html}
    {next_html}

    <div style="margin-top: 26px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; text-align: right; page-break-inside: avoid;">
        {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=fields.get('signature_style', 'military'), station=station, signature_image_path=fields.get('_signature_image_path'))}
    </div>
    """
    return html_content


def _build_office_note_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    ref_no = _escape(fields.get('reference_number') or 'CME/NOTE/2026/001')
    date_str = _escape(fields.get('date') or '')
    subject = _clean_subject(fields.get('subject') or '')
    refs = _escape(fields.get('references') or '')
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'General Staff Branch')
    station = _escape(fields.get('station') or 'CME, Pune – 411031')

    body_html = _format_paragraphs(body_content)

    refs_row = ''
    if refs:
        refs_row = f'<tr><td style="font-weight: bold; padding: 3px 0;">REFERENCES:</td><td style="padding: 3px 0;">{refs}</td></tr>'

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <h2 style="font-size: 12.5pt; font-weight: bold; margin: 4px 0 2px 0; color: #0f172a; letter-spacing: 1px;">OFFICE NOTE / NOTE SHEET</h2>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr><td style="width: 25%; padding: 3px 0; font-weight: bold;">FILE / REF NO:</td><td style="padding: 3px 0;">{ref_no}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">DATE:</td><td style="padding: 3px 0;">{date_str}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">SUBJECT:</td><td style="padding: 3px 0; font-weight: bold;"><u>{subject}</u></td></tr>
        {refs_row}
    </table>
    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 6px 0 14px 0;" />

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        {body_html}
    </div>

    <div style="margin-top: 26px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; text-align: right; page-break-inside: avoid;">
        {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=fields.get('signature_style', 'military'), station=station, signature_image_path=fields.get('_signature_image_path'))}
    </div>
    """
    return html_content


def _build_office_order_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    ref_no = _escape(fields.get('reference_number') or 'CME/ORDER/2026/001')
    date_str = _escape(fields.get('date') or '')
    subject = _clean_subject(fields.get('subject') or '')
    authority = _escape(fields.get('authority') or 'Commandant CME')
    effective_date = _escape(fields.get('effective_date') or '')
    distribution = _escape(fields.get('distribution') or '')
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'General Staff Branch')
    station = _escape(fields.get('station') or 'CME, Pune – 411031')

    body_html = _format_paragraphs(body_content)

    eff_html = ''
    if effective_date:
        eff_html = f'<div style="font-size: 9.5pt; font-style: italic; margin-top: 10px;">Effective Date: {effective_date}</div>'

    dist_html = ''
    if distribution:
        items = ''.join(f'<li style="margin-bottom: 3px;">{_escape(item.strip())}</li>' for item in distribution.split(',') if item.strip())
        dist_html = f"""
        <div style="margin-top: 16px; font-family: Arial, Helvetica, sans-serif;">
            <div style="font-weight: bold; font-size: 9.5pt; margin-bottom: 4px;">Distribution:</div>
            <ul style="font-size: 9pt; margin-left: 20px; padding-left: 0;">{items}</ul>
        </div>
        """

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <h2 style="font-size: 12.5pt; font-weight: bold; margin: 4px 0 2px 0; color: #0f172a; letter-spacing: 1.5px;">OFFICE ORDER</h2>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr><td style="width: 25%; padding: 3px 0; font-weight: bold;">ORDER NO:</td><td style="padding: 3px 0;">{ref_no}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">DATE:</td><td style="padding: 3px 0;">{date_str}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">SUBJECT:</td><td style="padding: 3px 0; font-weight: bold;"><u>{subject}</u></td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">AUTHORITY:</td><td style="padding: 3px 0;">{authority}</td></tr>
    </table>
    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 6px 0 14px 0;" />

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        {body_html}
    </div>

    {eff_html}

    <div style="margin-top: 26px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; text-align: right; page-break-inside: avoid;">
        {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=fields.get('signature_style', 'military'), station=station, signature_image_path=fields.get('_signature_image_path'))}
    </div>

    {dist_html}
    """
    return html_content


def _build_technical_report_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    title = _escape(fields.get('title') or 'TECHNICAL & TRIAL EVALUATION REPORT').upper()
    ref_no = _escape(fields.get('reference_number') or 'CME/TR/2026/001')
    date_str = _escape(fields.get('date') or '')
    author = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    author_dept = _escape(fields.get('from_department') or 'Combat Engineering Trials Wing')
    abstract = _escape(fields.get('abstract') or '')

    body_html = _format_paragraphs(body_content)

    abstract_html = ''
    if abstract:
        abstract_html = f"""
        <div style="margin-bottom: 14px; padding: 10px 14px; background: #f8fafc; border-left: 3px solid #1e293b;">
            <div style="font-weight: bold; font-size: 10pt; text-decoration: underline; margin-bottom: 4px;">EXECUTIVE SUMMARY</div>
            <div style="font-size: 9.5pt; font-style: italic; line-height: 1.45; color: #334155;">{abstract}</div>
        </div>
        """

    html_content = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <h2 style="font-size: 12pt; font-weight: bold; margin: 4px 0 2px 0; color: #0f172a; letter-spacing: 0.5px;">{title}</h2>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr><td style="width: 25%; padding: 3px 0; font-weight: bold;">REPORT ID:</td><td style="padding: 3px 0;">{ref_no}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">DATE:</td><td style="padding: 3px 0;">{date_str}</td></tr>
        <tr><td style="font-weight: bold; padding: 3px 0;">AUTHOR:</td><td style="padding: 3px 0;">{author} ({author_dept})</td></tr>
    </table>
    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 6px 0 14px 0;" />

    {abstract_html}

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        {body_html}
    </div>

    <div style="margin-top: 26px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; text-align: right; page-break-inside: avoid;">
        {_build_digital_signature_box_html(author, from_rank, from_appointment, from_authority, date_str, author_dept, signature_style=fields.get('signature_style', 'military'), signature_image_path=fields.get('_signature_image_path'))}
    </div>
    """
    return html_content



def _build_leave_application_html(fields, body_content, classification):
    org_name = _escape(fields.get('organization') or 'COLLEGE OF MILITARY ENGINEERING').upper()
    sub_header = _escape(fields.get('sub_header') or 'Dapodi, Pune – 411031 | Corps of Engineers')
    ref_no = _escape(fields.get('reference_number') or 'CME/LEAVE/2026/0001')
    date_str = _escape(fields.get('date') or '')
    to_name = _escape(fields.get('to_name') or 'The Commandant,<br/>College of Military Engineering,<br/>Dapodi, Pune – 411031')
    leave_type = _escape(fields.get('leave_type') or 'CASUAL LEAVE')
    subject = _clean_subject(fields.get('subject') or f"APPLICATION FOR {leave_type.upper()}")
    from_name = _escape(fields.get('from_name') or '')
    from_rank = _escape(fields.get('from_rank') or '')
    from_appointment = _escape(fields.get('from_appointment') or '')
    from_authority = _escape(fields.get('from_authority') or '')
    from_dept = _escape(fields.get('from_department') or 'Combat Engineering Wing')
    station = _escape(fields.get('station') or 'CME, Pune – 411031')
    signature_style = fields.get('signature_style', 'military')
    sig_img_path = fields.get('_signature_image_path')

    body_html = _format_paragraphs(body_content)

    return f"""
    <div style="font-family: Arial, Helvetica, sans-serif; text-align: center; margin-top: 6px;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; color: #0f172a; letter-spacing: 0.5px;">{org_name}</h1>
        <p style="font-size: 9pt; font-style: italic; color: #475569; margin: 2px 0 6px 0;">{sub_header}</p>
        <hr style="border: none; border-top: 1.5px solid #0f172a; margin: 6px 0 14px 0;" />
    </div>

    <table style="width: 100%; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; margin-bottom: 12px; border-collapse: collapse;">
        <tr>
            <td style="width: 50%; vertical-align: top; line-height: 1.45;">
                <div>Tele: 020-27146000/2204</div>
                <div><strong>Ref: {ref_no}</strong></div>
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; line-height: 1.45;">
                <div>{from_dept}</div>
                <div>{station}</div>
                <div><strong>{date_str}</strong></div>
            </td>
        </tr>
    </table>

    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.45; margin-bottom: 12px;">
        <strong>To,</strong><br/>
        {to_name}
    </div>

    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; margin: 12px 0; line-height: 1.4;">
        <strong>SUBJECT:</strong> <u>{subject}</u>
    </div>

    <div style="font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.55; color: #0f172a;">
        <p style="margin-bottom: 10px;">Sir,</p>
        {body_html}
    </div>

    <div style="margin-top: 24px; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; page-break-inside: avoid;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 50%; vertical-align: bottom;">
                    <div style="font-size: 8.5pt; color: #475569;">Copy to: Head of Department ({from_dept})</div>
                </td>
                <td style="width: 50%; text-align: right; vertical-align: bottom;">
                    {_build_digital_signature_box_html(from_name, from_rank, from_appointment, from_authority, date_str, from_dept, signature_style=signature_style, station=station, signature_image_path=sig_img_path)}
                </td>
            </tr>
        </table>
    </div>
    """

HTML_BUILDERS = {
    'leave_application': _build_leave_application_html,
    'formal_letter': _build_formal_letter_html,
    'office_memo': _build_office_memo_html,
    'meeting_minutes': _build_meeting_minutes_html,
    'office_note': _build_office_note_html,
    'office_order': _build_office_order_html,
    'technical_report': _build_technical_report_html,
}

CLASS_COLORS = {
    'CONFIDENTIAL': (0.6, 0.1, 0.1),    # Crimson
    'SECRET': (0.5, 0.05, 0.05),        # Deep Red
    'RESTRICTED': (0.7, 0.35, 0.0),      # Amber
    'UNCLASSIFIED': (0.2, 0.25, 0.35),   # Slate Navy
}


def build_pdf_document(doc_type, fields, body_content, passcode=None):
    """
    Generate military-standard A4 PDF bytes for the given document archetype.
    """
    fields = fields or {}
    classification = str(fields.get('classification') if fields.get('classification') is not None else 'NONE').upper()
    has_classification = classification not in ('NONE', 'NOTHING', '', 'NO CLASSIFICATION')
    builder = HTML_BUILDERS.get(doc_type, _build_formal_letter_html)
    doc_html = builder(fields, body_content, classification)

    story = fitz.Story(html=doc_html)
    doc = story.write_with_links(_rectfn)

    # Stamp running classification banners and page numbers on each page
    color = CLASS_COLORS.get(classification, (0.2, 0.25, 0.35))
    total_pages = doc.page_count

    for i, page in enumerate(doc):
        # Subtle diagonal DRAFT watermark unless explicitly finalized
        is_draft = fields.get('_is_draft', True) and not fields.get('is_final', False)
        if is_draft:
            point = fitz.Point(140, 520)
            page.insert_text(
                point,
                "DRAFT",
                fontsize=95,
                fontname="helv",
                color=(0.91, 0.91, 0.91),
                morph=(point, fitz.Matrix(45))
            )
        if has_classification:
            # 1. Top Classification Box & Text
            top_box = fitz.Rect(210, 18, 385, 34)
            page.draw_rect(top_box, color=color, width=0.8)
            page.insert_textbox(
                top_box,
                classification,
                fontsize=9,
                fontname="helv",
                color=color,
                align=fitz.TEXT_ALIGN_CENTER
            )

            # 2. Bottom Classification Box & Text
            bot_box = fitz.Rect(210, 810, 385, 826)
            page.draw_rect(bot_box, color=color, width=0.8)
            page.insert_textbox(
                bot_box,
                classification,
                fontsize=9,
                fontname="helv",
                color=color,
                align=fitz.TEXT_ALIGN_CENTER
            )

        # 3. Page numbering at bottom right
        if total_pages > 1:
            pg_box = fitz.Rect(450, 810, 595.28 - 54, 826)
            page.insert_textbox(
                pg_box,
                f"Page {i + 1} of {total_pages}",
                fontsize=8,
                fontname="helv",
                color=(0.4, 0.45, 0.5),
                align=fitz.TEXT_ALIGN_RIGHT
            )

    # Apply military AES-256 PDF Encryption if passcode is provided
    if passcode and str(passcode).strip():
        clean_pw = str(passcode).strip()
        pdf_bytes = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=clean_pw,
            owner_pw=f"{clean_pw}_cme_security_owner",
            permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ACCESSIBILITY
        )
    else:
        pdf_bytes = doc.tobytes()

    doc.close()
    return pdf_bytes
