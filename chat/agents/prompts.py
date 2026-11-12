"""
Prompt templates for document content generation.
Each document type has a focused prompt that asks the LLM to write ONLY body content.
"""


SYSTEM_PROMPT = (
    "You are a professional document writer for the College of Military Engineering (CME), Pune. "
    "Write formal, precise, military-standard content.\n\n"
    "Rules:\n"
    "- Use formal professional language\n"
    "- Be concise and authoritative\n"
    "- Use numbered paragraphs (1., 2., 3.)\n"
    "- Do NOT include headers, dates, addresses, reference numbers, or signatures\n"
    "- ONLY write the main body content paragraphs\n"
    "- Do NOT use markdown formatting\n"
)


CONTENT_PROMPTS = {
    'formal_letter': (
        "Write the body paragraphs for a formal military letter.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "To: {to_name}\n"
        "Key Points to Cover:\n{key_points}\n\n"
        "Write 3-5 well-structured numbered paragraphs. "
        "Start with a reference/introduction paragraph, cover the key points, "
        "and end with a request/action paragraph."
    ),
    'office_memo': (
        "Write the body paragraphs for an internal office memo/circular.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "To: {to}\n"
        "Key Points:\n{key_points}\n\n"
        "Write 2-4 concise numbered paragraphs. Be direct and action-oriented."
    ),
    'meeting_minutes': (
        "Write the minutes of meeting content.\n\n"
        "Meeting: {meeting_title}\n"
        "Chaired by: {chairperson}\n"
        "Attendees: {attendees}\n"
        "Agenda / Key Discussions:\n{agenda_items}\n\n"
        "Write structured numbered points covering each discussion item. "
        "For each item, note the discussion summary and any decisions taken. "
        "Be factual and concise."
    ),
    'office_note': (
        "Write the content for an office note / note sheet.\n\n"
        "Subject: {subject}\n"
        "From: {from_name}\n"
        "Background & Proposal:\n{key_points}\n\n"
        "Write 3-5 numbered paragraphs covering: "
        "1) Background/context, 2) Current situation, 3) Proposal, "
        "4) Justification, 5) Recommendation for approval."
    ),
    'office_order': (
        "Write the content for an official office order.\n\n"
        "Subject: {subject}\n"
        "Authority/Reference: {authority}\n"
        "Order Details:\n{key_points}\n\n"
        "Write numbered directive paragraphs. Be authoritative and unambiguous. "
        "End with an implementation/compliance paragraph."
    ),
    'technical_report': (
        "Write the content for a technical report.\n\n"
        "Title: {title}\n"
        "Author: {from_name}\n"
        "Sections to Cover:\n{key_points}\n\n"
        "Write structured sections with clear headings. Include: "
        "Introduction, detailed findings/analysis for each topic, "
        "and Conclusion with recommendations."
    ),
}

REVISION_PROMPT = (
    "Below is the original document body content:\n\n"
    "---\n{original_content}\n---\n\n"
    "Revise the above content based on this instruction:\n{revision_instruction}\n\n"
    "Output ONLY the revised body content. Do NOT add headers, dates, or signatures."
)


def build_content_prompt(doc_type, fields):
    """Build the LLM prompt for generating document content."""
    template = CONTENT_PROMPTS.get(doc_type)
    if not template:
        return f"Write professional body content for a document about: {fields.get('subject', fields.get('key_points', ''))}"

    # Fill template with available fields, using empty string for missing ones
    try:
        return template.format(**{k: v or '' for k, v in fields.items()})
    except KeyError:
        # If template has placeholders not in fields, do partial format
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
