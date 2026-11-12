"""
Prompt templates for document content generation.
Each document type has a focused prompt + a one-shot Indian Army style example.
"""

SYSTEM_PROMPT = (
    "You are a Staff Duties Officer at Headquarters, College of Military Engineering (CME), Pune. "
    "You draft official correspondence strictly in accordance with Indian Army Staff Duties conventions.\n\n"
    "Rules:\n"
    "- Use numbered paragraphs: 1., 2., 3. (sub-paragraphs: 1a., 1a(i).)\n"
    "- Use formal Indian Army phrasing: 'it is submitted', 'reference is invited', "
    "'necessary action', 'appended hereto', 'referred above', 'in view of the above'\n"
    "- Military rank abbreviations: Col, Lt Col, Maj, Capt, Hav, Sep\n"
    "- Write in active voice for orders; passive voice for submissions and memos\n"
    "- End letters with an action/request para\n"
    "- End orders with a compliance para\n"
    "- Do NOT include headers, dates, addresses, reference numbers, or signatures\n"
    "- ONLY write the main body content paragraphs\n"
    "- Do NOT use markdown formatting, bullet points, or bold text\n"
)

CONTENT_PROMPTS = {
    'formal_letter': (
        "Write the body paragraphs for a formal military letter.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "To: {to_name}\n"
        "Key Points to Cover:\n{key_points}\n\n"
        "Example of correct Indian Army style:\n"
        "1. Reference is invited to HQ CME letter No. CME/GEN/2024/0001 dated 10 Nov 2024 on the above subject.\n"
        "2. It is submitted that the annual equipment audit has been completed by the technical committee as per schedule.\n"
        "3. In view of the above, it is requested that administrative sanction may kindly be accorded to proceed further.\n\n"
        "Now write 3-5 well-structured numbered paragraphs following this style exactly. "
        "Start with a reference/introduction para, cover all key points, end with a request/action para."
    ),
    'office_memo': (
        "Write the body paragraphs for an internal office memo/circular.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "To: {to}\n"
        "Key Points:\n{key_points}\n\n"
        "Example of correct Indian Army memo style:\n"
        "1. This memorandum is issued to bring to the notice of all concerned the revised procedure for equipment indent.\n"
        "2. With effect from 01 Dec 2024, all indents shall be routed through the respective Wing QM.\n"
        "3. Strict compliance is expected. Any deviation shall be viewed seriously.\n\n"
        "Now write 2-4 concise numbered paragraphs following this style. Be direct and action-oriented."
    ),
    'meeting_minutes': (
        "Write the minutes of meeting content.\n\n"
        "Meeting: {meeting_title}\n"
        "Chaired by: {chairperson}\n"
        "Attendees: {attendees}\n"
        "Agenda / Key Discussions:\n{agenda_items}\n\n"
        "Example of correct Indian Army MoM style:\n"
        "1. A review meeting was convened on 10 Nov 2024 to deliberate upon the status of infrastructure projects.\n"
        "2. Discussion on Item 1 — Progress of Construction: The dealing officer briefed that work was 70 percent complete. "
        "The meeting decided that the remaining work shall be completed by 31 Dec 2024.\n"
        "3. The meeting concluded with directions to all project officers to submit weekly progress reports.\n\n"
        "Now write structured numbered points covering each discussion item with decisions taken. Be factual and concise."
    ),
    'office_note': (
        "Write the content for an office note / note sheet.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "Background & Proposal:\n{key_points}\n\n"
        "Example of correct Indian Army office note style:\n"
        "1. Background: The existing photocopy machine in the Admin office has been unserviceable since 05 Nov 2024.\n"
        "2. Current Situation: Procurement of a replacement machine is necessitated for smooth office functioning.\n"
        "3. Proposal: It is proposed to procure one photocopy machine at an estimated cost of Rs 45,000/-.\n"
        "4. Justification: The expenditure is essential and provision exists under head 'Office Machinery'.\n"
        "5. Recommendation: Put up for favorable consideration and sanction of the competent authority, please.\n\n"
        "Now write 3-5 numbered paragraphs covering Background, Current Situation, Proposal, Justification, Recommendation."
    ),
    'office_order': (
        "Write the content for an official office order.\n\n"
        "Subject: {subject}\n"
        "Authority/Reference: {authority}\n"
        "Order Details:\n{key_points}\n\n"
        "Example of correct Indian Army office order style:\n"
        "1. In exercise of the powers vested by the Commandant, CME, the following instructions are promulgated with immediate effect.\n"
        "2. All personnel shall report to duty by 0730 hours on working days with effect from 01 Dec 2024.\n"
        "3. Defaulters shall be liable for disciplinary action under the provisions of Army Act.\n"
        "4. All heads of departments shall ensure strict compliance and intimate this HQ of any non-compliance forthwith.\n\n"
        "Now write numbered directive paragraphs following this style. Be authoritative and unambiguous. "
        "End with a compliance paragraph."
    ),
    'technical_report': (
        "Write the content for a technical report.\n\n"
        "Title: {title}\n"
        "Author: {from_name}\n"
        "Sections to Cover:\n{key_points}\n\n"
        "Write structured sections with clear headings. Include: "
        "Introduction, detailed findings/analysis for each topic, "
        "and Conclusion with recommendations. Be precise and technical."
    ),
    'leave_application': (
        "Write the content for a formal leave application.\n\n"
        "Applicant: {from_name}\n"
        "Leave Type: {leave_type}\n"
        "From Date: {from_date}\n"
        "To Date: {to_date}\n"
        "Reason: {key_points}\n\n"
        "Example of correct Indian Army leave application:\n"
        "1. It is respectfully submitted that the undersigned wishes to proceed on Casual Leave for 03 days "
        "from 15 Nov 2024 to 17 Nov 2024 (both days inclusive).\n"
        "2. The purpose of the leave is to attend to urgent family matters at the home station.\n"
        "3. The duties of the undersigned during the period of absence shall be looked after by Capt R Singh.\n"
        "4. It is requested that leave may kindly be sanctioned.\n\n"
        "Now write a formal leave application following this style exactly."
    ),
}

REVISION_PROMPT = (
    "Below is the original document body content:\n\n"
    "---\n{original_content}\n---\n\n"
    "Revise the above content based on this instruction:\n{revision_instruction}\n\n"
    "Output ONLY the revised body content in Indian Army Staff Duties style. "
    "Do NOT add headers, dates, or signatures."
)


def build_content_prompt(doc_type, fields):
    """Build the LLM prompt for generating document content."""
    template = CONTENT_PROMPTS.get(doc_type)
    if not template:
        return f"Write professional Indian Army Staff Duties body content for a document about: {fields.get('subject', fields.get('key_points', ''))}"

    try:
        return template.format(**{k: v or '' for k, v in fields.items()})
    except KeyError:
        result = template
        for key, value in fields.items():
            result = result.replace('{' + key + '}', value or '')
        return result


def build_revision_prompt(original_content, revision_instruction):
    """Build the LLM prompt for revising existing content."""
    return REVISION_PROMPT.format(
        original_content=original_content,
        revision_instruction=revision_instruction,
    )
