"""
Management command to backup the database.
Supports SQLite and PostgreSQL.
"""
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Backup the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove backups older than retention period',
        )
        parser.add_argument(
            '--database',
            type=str,
            default='default',
            help='Database alias to backup (default: default)',
        )

    def handle(self, *args, **options):
        backup_dir = settings.DB_BACKUP_DIR
        backup_dir.mkdir(exist_ok=True)

        db_settings = settings.DATABASES[options['database']]
        db_engine = db_settings['ENGINE']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if 'sqlite' in db_engine:
            self._backup_sqlite(db_settings, backup_dir, timestamp)
        elif 'postgresql' in db_engine:
            self._backup_postgresql(db_settings, backup_dir, timestamp)
        else:
            raise CommandError(f'Unsupported database engine: {db_engine}')

        if options['cleanup']:
            self._cleanup_old_backups(backup_dir)

        self.stdout.write(
            self.style.SUCCESS(f'Database backup completed: {backup_dir}')
        )

    def _backup_sqlite(self, db_settings, backup_dir, timestamp):
        """Backup SQLite database"""
        db_path = Path(db_settings['NAME'])
        if not db_path.exists():
            raise CommandError(f'SQLite database not found: {db_path}')

        backup_file = backup_dir / f'nexuside_backup_{timestamp}.sqlite3'
        shutil.copy2(db_path, backup_file)

        # Also create a compressed copy
        compressed_file = backup_dir / f'nexuside_backup_{timestamp}.sqlite3.gz'
        import gzip
        with open(db_path, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        self.stdout.write(f'  SQLite backup: {backup_file.name}')
        self.stdout.write(f'  Compressed: {compressed_file.name}')

    def _backup_postgresql(self, db_settings, backup_dir, timestamp):
        """Backup PostgreSQL database using pg_dump"""
        backup_file = backup_dir / f'nexuside_backup_{timestamp}.sql'

        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']

        cmd = [
            'pg_dump',
            '-h', db_settings['HOST'],
            '-p', str(db_settings['PORT']),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', str(backup_file),
            '--clean',
            '--if-exists',
        ]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
            self.stdout.write(f'  PostgreSQL backup: {backup_file.name}')
        except subprocess.CalledProcessError as e:
            raise CommandError(f'pg_dump failed: {e.stderr}')
        except FileNotFoundError:
            raise CommandError('pg_dump not found. Install PostgreSQL client tools.')

    def _cleanup_old_backups(self, backup_dir):
        """Remove backups older than retention period"""
        retention_days = settings.DB_BACKUP_RETENTION_DAYS
        cutoff = datetime.now().timestamp() - (retention_days * 86400)

        removed = 0
        for f in backup_dir.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1

        if removed:
            self.stdout.write(f'  Cleaned up {removed} old backup(s)')
