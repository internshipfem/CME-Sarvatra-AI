"""
DOCX Builder — Core orchestrator for converting fields + LLM body into DOCX byte stream.
Zero LLM required for formatting.
"""

import io
from .templates.formal_letter import build_formal_letter
from .templates.office_memo import build_office_memo
from .templates.meeting_minutes import build_meeting_minutes
from .templates.extended_templates import (
    build_office_note,
    build_office_order,
    build_technical_report,
)

BUILDERS = {
    'formal_letter': build_formal_letter,
    'office_memo': build_office_memo,
    'meeting_minutes': build_meeting_minutes,
    'office_note': build_office_note,
    'office_order': build_office_order,
    'technical_report': build_technical_report,
}


def build_document(doc_type, fields, body_content):
    """
    Build DOCX document and return bytes.
    doc_type: string ('formal_letter', 'office_memo', etc.)
    fields: dict with metadata
    body_content: string with LLM-generated body text
    """
    builder_fn = BUILDERS.get(doc_type, build_formal_letter)
    doc = builder_fn(fields, body_content)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()
