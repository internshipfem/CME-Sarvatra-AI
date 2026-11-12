"""
Field extraction from user messages — regex, NOT LLM.
Also handles auto-filling sender info from user profile.
"""

import re


# Required fields per document type
REQUIRED_FIELDS = {
    'formal_letter': {
        'to_name': {'label': 'To (Name & Designation)', 'prompt': 'Who is this letter addressed to? (Name & Designation)'},
        'subject': {'label': 'Subject', 'prompt': 'What is the subject of this letter?'},
        'key_points': {'label': 'Key Points', 'prompt': 'What key points should the letter cover? (brief bullet points)'},
    },
    'office_memo': {
        'to': {'label': 'To (Department/Person)', 'prompt': 'Who is this memo addressed to?'},
        'subject': {'label': 'Subject', 'prompt': 'What is the subject of this memo?'},
        'key_points': {'label': 'Key Points / Body', 'prompt': 'What should the memo cover?'},
    },
    'meeting_minutes': {
        'meeting_title': {'label': 'Meeting Title', 'prompt': 'What was the meeting title/topic?'},
        'venue': {'label': 'Venue', 'prompt': 'Where was the meeting held?'},
        'chairperson': {'label': 'Chairperson', 'prompt': 'Who chaired the meeting?'},
        'attendees': {'label': 'Attendees', 'prompt': 'Who attended? (comma-separated names)'},
        'agenda_items': {'label': 'Agenda / Key Discussions', 'prompt': 'What were the main agenda items and discussions?'},
    },
    'office_note': {
        'subject': {'label': 'Subject', 'prompt': 'What is the subject of this note?'},
        'key_points': {'label': 'Background & Proposal', 'prompt': 'What is the background and what are you proposing?'},
    },
    'office_order': {
        'subject': {'label': 'Subject', 'prompt': 'What is this order about?'},
        'authority': {'label': 'Authority / Reference', 'prompt': 'Under what authority or reference is this order issued?'},
        'key_points': {'label': 'Order Details', 'prompt': 'What are the key directives/instructions?'},
    },
    'technical_report': {
        'title': {'label': 'Report Title', 'prompt': 'What is the title of this report?'},
        'key_points': {'label': 'Sections & Content', 'prompt': 'What topics/sections should the report cover?'},
    },
    'leave_application': {
        'leave_type': {'label': 'Leave Type', 'prompt': 'What type of leave? (Casual Leave / Annual Leave / Station Leave)'},
        'from_date': {'label': 'From Date', 'prompt': 'From which date? (DD MMM YYYY)'},
        'to_date': {'label': 'To Date', 'prompt': 'To which date? (DD MMM YYYY)'},
        'key_points': {'label': 'Reason for Leave', 'prompt': 'State the reason for proceeding on leave.'},
    },
}

# Optional fields per document type
OPTIONAL_FIELDS = {
    'formal_letter': {
        'cc_list': {'label': 'CC List', 'prompt': 'Anyone to CC? (comma-separated, or skip)'},
        'enclosures': {'label': 'Enclosures', 'prompt': 'Any enclosures to mention? (or skip)'},
    },
    'office_memo': {
        'action_required': {'label': 'Action Required', 'prompt': 'Any specific action required? (or skip)'},
    },
    'meeting_minutes': {
        'action_items': {'label': 'Action Items', 'prompt': 'Any action items with owners? (or skip)'},
        'next_meeting': {'label': 'Next Meeting Date', 'prompt': 'When is the next meeting? (or skip)'},
    },
    'office_note': {
        'references': {'label': 'References', 'prompt': 'Any reference documents? (or skip)'},
    },
    'office_order': {
        'effective_date': {'label': 'Effective Date', 'prompt': 'When does this take effect? (default: today, or skip)'},
        'distribution': {'label': 'Distribution List', 'prompt': 'Distribution list? (or skip)'},
    },
    'technical_report': {
        'abstract': {'label': 'Abstract/Summary', 'prompt': 'Brief abstract? (or let AI generate)'},
    },
    'leave_application': {
        'station_address': {'label': 'Station / Contact Address During Leave', 'prompt': 'Address or contact during leave? (or skip)'},
        'relieving_officer': {'label': 'Relieving / Handover Officer', 'prompt': 'Name of relieving officer? (or skip)'},
    },
}


def get_required_fields(doc_type):
    """Return the required fields definition for a document type."""
    return REQUIRED_FIELDS.get(doc_type, {})


def get_optional_fields(doc_type):
    """Return the optional fields definition for a document type."""
    return OPTIONAL_FIELDS.get(doc_type, {})


def extract_fields_from_message(message, doc_type):
    """
    Extract obvious fields from user message using regex. Pure Python.
    Returns a dict of field_name -> extracted_value.
    """
    fields = {}

    # Extract "to [person/org]" pattern
    to_match = re.search(
        r'(?:to|addressed?\s+to)\s+(?:the\s+)?(.+?)(?:\s+about|\s+regarding|\s+for|\s+subject|[,.]|$)',
        message, re.IGNORECASE
    )
    if to_match:
        val = to_match.group(1).strip()
        if len(val) > 2:
            if doc_type == 'formal_letter':
                fields['to_name'] = val
            else:
                fields['to'] = val

    # Extract "about/regarding [subject]" pattern
    subject_match = re.search(
        r'(?:about|regarding|subject|on the topic of)\s+(.+?)(?:\.|,\s+(?:key|include|cover|mention)|$)',
        message, re.IGNORECASE
    )
    if subject_match:
        val = subject_match.group(1).strip()
        if len(val) > 2:
            fields['subject'] = val

    return fields


def auto_fill_sender(user):
    """Pull sender details from logged-in user's profile. No LLM."""
    profile = getattr(user, 'profile', None)
    full_name = f"{user.first_name} {user.last_name}".strip()
    return {
        'from_name': full_name or user.username,
        'from_employee_id': profile.employee_id if profile else '',
        'from_department': (profile.department if profile and profile.department else 'Combat Engineering Wing'),
        'from_rank': profile.rank if profile else '',
        'from_appointment': profile.appointment if profile else '',
        'from_authority': profile.authority if profile else '',
        'signature_style': profile.signature_style if profile else 'military',
        'signature_text': profile.signature_text if profile else '',
    }


def check_missing_fields(doc_type, collected_fields):
    """
    Check which required fields are still missing.
    Returns list of (field_name, field_info) tuples for missing fields.
    """
    required = get_required_fields(doc_type)
    missing = []
    for field_name, field_info in required.items():
        if field_name not in collected_fields or not collected_fields[field_name]:
            missing.append((field_name, field_info))
    return missing
