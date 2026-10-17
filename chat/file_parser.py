import os
import logging

logger = logging.getLogger(__name__)

# Max characters of extracted text to include in prompt context (to avoid exceeding Ollama context)
MAX_EXTRACTED_CHARS = 35000


def extract_text_from_file(file_path, original_filename=None):
    """
    Extract readable text from uploaded files (text, code, json, csv, pdf, docx).
    Returns extracted string content and a status message.
    """
    filename = original_filename or os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    extracted = ""
    try:
        # 1. Plain text / Code / Structured text
        text_extensions = {
            '.txt', '.md', '.markdown', '.py', '.js', '.jsx', '.ts', '.tsx',
            '.html', '.htm', '.css', '.scss', '.json', '.xml', '.yaml', '.yml',
            '.csv', '.tsv', '.sql', '.log', '.ini', '.cfg', '.conf', '.env',
            '.bat', '.ps1', '.sh', '.c', '.cpp', '.h', '.hpp', '.java', '.cs',
            '.go', '.rs', '.php', '.rb', '.r', '.dockerfile'
        }

        if ext in text_extensions or ext == '' or filename.startswith('.'):
            # Attempt reading with various encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            content = None
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc, errors='replace') as f:
                        content = f.read()
                    break
                except Exception:
                    continue
            if content is not None:
                extracted = content

        # 2. PDF Files
        elif ext == '.pdf':
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(file_path)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages_text.append(f"--- Page {idx + 1} ---\n{page_text}")
                extracted = "\n\n".join(pages_text)
            except Exception as e:
                logger.error(f"Error parsing PDF {filename}: {e}")
                extracted = f"[Error reading PDF: {e}]"

        # 3. Word Documents (.docx)
        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(file_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                extracted = "\n".join(paragraphs)
            except Exception as e:
                logger.error(f"Error parsing DOCX {filename}: {e}")
                extracted = f"[Error reading DOCX: {e}]"

        else:
            # Fallback binary or unknown: try text read anyway
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
        extracted = extracted[:MAX_EXTRACTED_CHARS] + f"\n\n[... Note: File truncated to first {MAX_EXTRACTED_CHARS} of {original_len} characters ...]"

    return extracted
