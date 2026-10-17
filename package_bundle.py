import os
import zipfile
import sys

OUTPUT_ZIP = 'Ollama_Chat_AirGapped_Bundle.zip'

# Directories and files to exclude from the release bundle
EXCLUDE_DIRS = {
    'venv',
    'env',
    '__pycache__',
    '.git',
    '.vscode',
    '.idea',
    'staticfiles'
}

EXCLUDE_FILES = {
    OUTPUT_ZIP,
    'db.sqlite3',
    'db.sqlite3-journal',
    '.gitignore'
}

EXCLUDE_EXTENSIONS = {
    '.pyc',
    '.pyo',
    '.pyd',
    '.zip'
}

def should_exclude(rel_path):
    parts = rel_path.replace('\\', '/').split('/')
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
        if p.startswith('.'):
            return True

    filename = parts[-1]
    if filename in EXCLUDE_FILES:
        return True

    # Exclude uploaded media files, keep empty media folder
    if 'media/uploads' in rel_path.replace('\\', '/'):
        return True

    ext = os.path.splitext(filename)[1].lower()
    if ext in EXCLUDE_EXTENSIONS:
        return True

    return False


def build_bundle():
    print(f"[*] Packaging project into {OUTPUT_ZIP}...")
    base_dir = os.path.abspath(os.path.dirname(__file__))
    zip_path = os.path.join(base_dir, OUTPUT_ZIP)

    # Remove existing zip if present
    if os.path.exists(zip_path):
        os.remove(zip_path)

    file_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, base_dir)

                if should_exclude(rel_path):
                    continue

                zf.write(abs_path, rel_path)
                file_count += 1

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[OK] Successfully created {OUTPUT_ZIP}")
    print(f"[*] Total files bundled: {file_count}")
    print(f"[*] Bundle archive size: {size_mb:.2f} MB")


if __name__ == '__main__':
    build_bundle()
