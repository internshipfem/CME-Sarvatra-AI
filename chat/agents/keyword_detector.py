"""
Document type detection via keyword matching — NO LLM call.
User clicks a card (primary) or types in chat (fallback regex matching).
"""

import re


# Keywords mapped to each document type (lowercase)
KEYWORD_MAP = {
    'formal_letter': [
        'letter', 'write to', 'correspondence', 'address to',
        'send to', 'communicate to', 'draft a letter', 'formal letter',
    ],
    'office_memo': [
        'memo', 'memorandum', 'circular', 'internal note',
        'office memo', 'department circular',
    ],
    'meeting_minutes': [
        'minutes', 'mom', 'meeting minutes', 'proceedings',
        'minutes of meeting', 'record of meeting',
    ],
    'office_note': [
        'note', 'note sheet', 'office note', 'file note',
        'noting', 'put up',
    ],
    'office_order': [
        'order', 'office order', 'directive', 'instruction',
        'standing order',
    ],
    'technical_report': [
        'report', 'technical report', 'assessment',
        'analysis report', 'findings',
    ],
    'leave_application': [
        'leave', 'leave application', 'casual leave', 'annual leave',
        'station leave', 'apply for leave', 'leave request', 'earned leave',
    ],
}

# Human-readable labels
DOCUMENT_TYPE_LABELS = {
    'formal_letter': 'Formal Letter',
    'office_memo': 'Office Memo / Circular',
    'meeting_minutes': 'Meeting Minutes (MoM)',
    'office_note': 'Office Note / Note Sheet',
    'office_order': 'Office Order',
    'technical_report': 'Technical Report',
    'leave_application': 'Leave Application',
}

DOCUMENT_TYPE_ICONS = {
    'formal_letter': 'DOC',
    'office_memo': 'MEMO',
    'meeting_minutes': 'MOM',
    'office_note': 'NOTE',
    'office_order': 'ORDER',
    'technical_report': 'REPORT',
    'leave_application': 'LEAVE',
}


def detect_document_type(user_message):
    """
    Pure Python keyword matching — no LLM call.
    Returns (doc_type, confidence) or (None, 0) if no match.
    """
    message_lower = user_message.lower()
    scores = {}

    for doc_type, keywords in KEYWORD_MAP.items():
        score = 0
        for kw in keywords:
            if kw in message_lower:
                # Longer keyword matches get higher weight
                score += len(kw.split())
        if score > 0:
            scores[doc_type] = score

    if not scores:
        return None, 0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Confidence: high if score >= 3, medium if 2, low if 1
    confidence = min(best_score / 3.0, 1.0)
    return best_type, confidence


def get_all_document_types():
    """Return list of all document types with labels and icons."""
    result = []
    for doc_type in KEYWORD_MAP:
        result.append({
            'type': doc_type,
            'label': DOCUMENT_TYPE_LABELS.get(doc_type, doc_type),
            'icon': DOCUMENT_TYPE_ICONS.get(doc_type, '📄'),
        })
    return result
