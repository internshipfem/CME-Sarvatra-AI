"""
Management command: python manage.py backup_db
Backs up db.sqlite3 to backups/ directory. Keeps last 7 backups.
Air-gap compliant backup management for CME Pune node.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Backup the SQLite database safely to backups/ directory. Keeps last 7 backups.'

    def handle(self, *args, **kwargs):
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f'Database file not found at {db_path}'))
            return

        backup_dir = db_path.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = backup_dir / f'db_{timestamp}.sqlite3'

        try:
            shutil.copy2(db_path, dest)
            size_kb = os.path.getsize(dest) / 1024
            self.stdout.write(self.style.SUCCESS(f'[OK] Database backup created: {dest.name} ({size_kb:.1f} KB)'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to copy database: {e}'))
            return

        # Retention policy: Keep only last 7 backups
        backups = sorted(backup_dir.glob('db_*.sqlite3'))
        while len(backups) > 7:
            oldest = backups.pop(0)
            try:
                oldest.unlink()
                self.stdout.write(f'[Pruned] Removed old database backup: {oldest.name}')
            except Exception:
                pass
