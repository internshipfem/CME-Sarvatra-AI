# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

BASE_DIR = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(BASE_DIR, 'templates'), 'templates'),
    (os.path.join(BASE_DIR, 'static'), 'static'),
]

hiddenimports = [
    'chat',
    'chat.apps',
    'chat.models',
    'chat.views',
    'chat.urls',
    'chat.ollama_client',
    'chat.file_parser',
    'chat.forms',
    'ollama_web',
    'ollama_web.urls',
    'ollama_web.wsgi',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.db.backends.sqlite3',
    'django.core.management.commands.runserver',
    'django.core.management.commands.migrate',
    'requests',
    'PyPDF2',
    'docx',
    'lxml',
]

a = Analysis(
    ['run_desktop.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'tensorflow', 'tensorboard', 'keras', 'cv2', 'tensorflow_io_gcs_filesystem'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SarvatraAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
