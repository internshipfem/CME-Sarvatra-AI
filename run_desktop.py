import os
import sys
import threading
import time
import webbrowser
import django
from django.core.management import call_command

# Ensure environment is configured
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ollama_web.settings')
django.setup()


def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open('http://127.0.0.1:8000')
    except Exception:
        pass


def main():
    print("=" * 65)
    print("     Sarvatra AI - College of Military Engineering, Pune")
    print("=" * 65)
    print("\n[*] Verifying database and admin account...")
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"[Notice] Migration: {e}")

    print("[*] Opening application in browser: http://127.0.0.1:8000 ...")
    threading.Thread(target=open_browser, daemon=True).start()

    print("[*] Server active. Close this console window to exit.\n")
    try:
        call_command('runserver', '127.0.0.1:8000', use_reloader=False)
    except KeyboardInterrupt:
        print("\nExiting Sarvatra AI.")


if __name__ == '__main__':
    main()
