"""Command-line interface for encrypted local database backups."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from app.backup import (
    BackupError,
    create_encrypted_backup,
    restore_encrypted_backup,
    verify_encrypted_backup,
)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="NILE ONE encrypted SQLite backup tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="Create an encrypted backup")
    create.add_argument("--output", default="backups/nile-one.sqlite.enc")
    verify = subparsers.add_parser("verify", help="Verify an encrypted backup")
    verify.add_argument("--input", required=True)
    restore = subparsers.add_parser("restore", help="Restore an encrypted backup")
    restore.add_argument("--input", required=True)
    restore.add_argument("--output", default="data/restored.sqlite3")
    restore.add_argument("--force", action="store_true")
    args = parser.parse_args()

    key = os.getenv("BACKUP_ENCRYPTION_KEY", "").strip()
    if len(key) < 40:
        parser.error("BACKUP_ENCRYPTION_KEY is missing. Run install_windows.bat to generate it.")
    database = Path(os.getenv("DATABASE_PATH", "./data/imd_dawsa.sqlite3"))
    try:
        if args.command == "create":
            path = create_encrypted_backup(database, args.output, key)
            print(f"Encrypted backup created: {path}")
        elif args.command == "verify":
            verify_encrypted_backup(args.input, key)
            print("Backup integrity and encryption verified.")
        else:
            path = restore_encrypted_backup(args.input, args.output, key, force=args.force)
            print(f"Database restored to: {path}")
    except BackupError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
