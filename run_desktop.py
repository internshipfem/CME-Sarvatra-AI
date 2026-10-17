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


import socket

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'


def main():
    lan_ip = get_lan_ip()
    print("=" * 65)
    print("     Sarvatra AI - College of Military Engineering, Pune")
    print("=" * 65)
    print("\n[*] Verifying database and admin account...")
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"[Notice] Migration: {e}")

    print("[*] Opening local browser: http://127.0.0.1:8000 ...")
    threading.Thread(target=open_browser, daemon=True).start()

    print("[*] Server active on 0.0.0.0:8000 (accessible on local network / web)")
    print(f"[*] Local Access:   http://127.0.0.1:8000")
    print(f"[*] Network Access: http://{lan_ip}:8000")
    print("    Close this console window to exit.\n")
    try:
        call_command('runserver', '0.0.0.0:8000', use_reloader=False)
    except KeyboardInterrupt:
        print("\nExiting Sarvatra AI.")


if __name__ == '__main__':
    main()
