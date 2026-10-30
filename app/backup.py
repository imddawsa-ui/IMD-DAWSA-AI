"""Encrypted SQLite backup, verification and guarded restore utilities."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class BackupError(RuntimeError):
    """Raised when a backup cannot be created, verified or restored."""


def _cipher(key: str | bytes) -> Fernet:
    raw = key.encode("ascii") if isinstance(key, str) else key
    try:
        return Fernet(raw)
    except (ValueError, TypeError) as exc:
        raise BackupError("Invalid backup encryption key") from exc


def _integrity_check(path: Path) -> None:
    try:
        with sqlite3.connect(str(path)) as db:
            result = db.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise BackupError("Database integrity check failed") from exc
    if not result or result[0] != "ok":
        raise BackupError("Database integrity check failed")


def create_encrypted_backup(database_path: str | Path, destination: str | Path,
                            encryption_key: str | bytes) -> Path:
    source = Path(database_path)
    target = Path(destination)
    if not source.is_file():
        raise BackupError("Source database does not exist")
    target.parent.mkdir(parents=True, exist_ok=True)
    cipher = _cipher(encryption_key)
    temporary_plain = None
    temporary_encrypted = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".sqlite", delete=False) as handle:
            temporary_plain = Path(handle.name)
        with sqlite3.connect(str(source)) as source_db, sqlite3.connect(str(temporary_plain)) as target_db:
            source_db.backup(target_db)
        _integrity_check(temporary_plain)
        encrypted = cipher.encrypt(temporary_plain.read_bytes())
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".enc", delete=False) as handle:
            temporary_encrypted = Path(handle.name)
            handle.write(encrypted)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_encrypted, target)
        temporary_encrypted = None
        return target
    except (OSError, sqlite3.DatabaseError) as exc:
        raise BackupError("Backup creation failed") from exc
    finally:
        for path in (temporary_plain, temporary_encrypted):
            if path:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def verify_encrypted_backup(backup_path: str | Path, encryption_key: str | bytes) -> bool:
    source = Path(backup_path)
    temporary = None
    try:
        plaintext = _cipher(encryption_key).decrypt(source.read_bytes())
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(plaintext)
            handle.flush()
        _integrity_check(temporary)
        return True
    except (OSError, InvalidToken) as exc:
        raise BackupError("Backup verification failed") from exc
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def restore_encrypted_backup(backup_path: str | Path, database_path: str | Path,
                             encryption_key: str | bytes, *, force: bool = False) -> Path:
    target = Path(database_path)
    if target.exists() and not force:
        raise BackupError("Target database exists; explicit force is required")
    temporary = None
    try:
        plaintext = _cipher(encryption_key).decrypt(Path(backup_path).read_bytes())
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".restore", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(plaintext)
            handle.flush()
            os.fsync(handle.fileno())
        _integrity_check(temporary)
        os.replace(temporary, target)
        temporary = None
        return target
    except (OSError, InvalidToken) as exc:
        raise BackupError("Restore failed; target database was not replaced") from exc
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
