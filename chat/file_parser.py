import os
import re
import logging
import zipfile
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Max characters of extracted text to include in prompt context (to avoid exceeding Ollama context)
MAX_EXTRACTED_CHARS = 40000


def extract_text_from_file(file_path, original_filename=None):
    """
    Extract readable text from uploaded files (text, code, json, csv, pdf, doc, docx).
    Returns extracted string content.
    """
    filename = original_filename or os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    extracted = ""
    try:
        # 1. Plain text / Code / Structured data
        text_extensions = {
            '.txt', '.md', '.markdown', '.py', '.js', '.jsx', '.ts', '.tsx',
            '.html', '.htm', '.css', '.scss', '.json', '.xml', '.yaml', '.yml',
            '.csv', '.tsv', '.sql', '.log', '.ini', '.cfg', '.conf', '.env',
            '.bat', '.ps1', '.sh', '.c', '.cpp', '.h', '.hpp', '.java', '.cs',
            '.go', '.rs', '.php', '.rb', '.r', '.dockerfile'
        }

        if ext in text_extensions or ext == '' or filename.startswith('.'):
            encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1', 'gb18030']
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc, errors='replace') as f:
                        extracted = f.read()
                    break
                except Exception:
                    continue

        # 2. PDF Files
        elif ext == '.pdf':
            extracted = _extract_pdf(file_path, filename)

        # 3. Modern Word Documents (.docx)
        elif ext == '.docx':
            extracted = _extract_docx(file_path, filename)

        # 4. Legacy Word Documents (.doc)
        elif ext == '.doc':
            extracted = _extract_doc(file_path, filename)

        else:
            # Fallback: attempt text read anyway
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted = f.read(50000)
            except Exception as e:
                extracted = f"[Binary or unsupported file format: {ext}]"

    except Exception as e:
        logger.error(f"Error processing file {filename}: {e}")
        extracted = f"[Failed to extract text from {filename}: {str(e)}]"

    # Clean and check character length
    if len(extracted) > MAX_EXTRACTED_CHARS:
        original_len = len(extracted)
        extracted = extracted[:MAX_EXTRACTED_CHARS] + f"\n\n[... Note: Document truncated to first {MAX_EXTRACTED_CHARS} of {original_len} characters ...]"

    return extracted


def _extract_pdf(file_path, filename):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        if reader.is_encrypted:
            try:
                reader.decrypt('')
            except Exception:
                pass

        pages_text = []
        for idx, page in enumerate(reader.pages):
            page_text = ""
            try:
                page_text = page.extract_text() or ""
            except Exception:
                pass
            if page_text.strip():
                pages_text.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")

        extracted = "\n\n".join(pages_text)
        if not extracted.strip():
            extracted = (
                f"[Notice: No selectable digital text was found in '{filename}'. "
                f"This document appears to be a scanned image or photograph saved as a PDF. "
                f"Without optical character recognition (OCR), text inside image scans cannot be read directly. "
                f"Please upload a document with digital selectable text (such as a Word .docx, .doc, .txt, or digital PDF with text).]"
            )
        return extracted
    except Exception as e:
        logger.error(f"Error parsing PDF {filename}: {e}")
        return f"[Error reading PDF {filename}: {e}]"


def _extract_docx(file_path, filename):
    # Method A: python-docx (paragraphs + tables)
    try:
        import docx
        doc = docx.Document(file_path)
        parts = []

        # Paragraphs
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                parts.append(txt)

        # Tables
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        extracted = "\n\n".join(parts)
        if extracted.strip():
            return extracted
    except Exception as e:
        logger.warning(f"python-docx parsing failed on {filename}, attempting XML fallback: {e}")

    # Method B: Direct XML extraction from docx zip container
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            xml_content = z.read('word/document.xml')
        root = ET.fromstring(xml_content)
        texts = []
        for elem in root.iter():
            if elem.tag.endswith('}t') and elem.text:
                texts.append(elem.text)
        return " ".join(texts)
    except Exception as e:
        logger.error(f"Error parsing DOCX {filename}: {e}")
        return f"[Error reading DOCX {filename}: {e}]"


def _extract_doc(file_path, filename):
    """
    Extract readable text runs from legacy binary Word (.doc) files.
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # Extract UTF-16LE text runs (min 3 readable characters)
        utf16_runs = re.findall(rb'(?:[\x20-\x7e\r\n\t]\x00){3,}', content)
        utf16_texts = [r.decode('utf-16le', errors='ignore').strip() for r in utf16_runs]

        # Extract ASCII/ANSI runs (min 4 readable characters)
        ascii_runs = re.findall(rb'[\x20-\x7e\r\n\t]{4,}', content)
        ascii_texts = [r.decode('latin-1', errors='ignore').strip() for r in ascii_runs]

        # Filter out common OLE binary metadata strings
        noise = {
            'Normal.dot', 'Microsoft Word', 'Root Entry', 'WordDocument',
            'SummaryInformation', 'DocumentSummaryInformation', 'CompObj',
            'Table', 'Data', 'ObjectPool', 'Times New Roman', 'Arial', 'Calibri'
        }

        # Choose the representation with higher total content
        all_candidates = utf16_texts if sum(len(x) for x in utf16_texts) > sum(len(x) for x in ascii_texts) else ascii_texts
        valid_blocks = []
        for block in all_candidates:
            cleaned = block.strip()
            if len(cleaned) >= 2 and cleaned not in noise:
                valid_blocks.append(cleaned)

        if valid_blocks:
            return "\n\n".join(valid_blocks)
        return f"[Notice: Could not extract readable text from legacy binary Word file '{filename}'. Please re-save as .docx or .txt.]"
    except Exception as e:
        logger.error(f"Error parsing DOC {filename}: {e}")
        return f"[Error reading legacy DOC {filename}: {e}]"
