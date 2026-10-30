import sqlite3
from pathlib import Path
from .config import settings


def connect():
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                handle TEXT UNIQUE,
                bio TEXT NOT NULL DEFAULT '',
                email_verified INTEGER NOT NULL DEFAULT 0,
                totp_secret_enc TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(conversations)").fetchall()}
        if "user_id" not in columns:
            db.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "handle" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN handle TEXT")
        if "bio" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''")
        if "email_verified" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        if "totp_secret_enc" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN totp_secret_enc TEXT")
        if "totp_enabled" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN totp_enabled INTEGER NOT NULL DEFAULT 0")
        db.execute("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS two_factor_recovery_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("UPDATE users SET handle = 'user' || id WHERE handle IS NULL OR handle = ''")
        # Repair duplicate legacy handles before enforcing uniqueness on upgraded databases.
        db.execute("""
            UPDATE users
            SET handle = 'user' || id
            WHERE id IN (
                SELECT id FROM users
                GROUP BY handle HAVING COUNT(*) > 1
            )
        """)
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_handle_unique ON users(handle)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                visibility TEXT NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'followers', 'private')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS follows (
                follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (follower_id, following_id),
                CHECK (follower_id <> following_id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS post_likes (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, post_id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id_id ON conversations(user_id, id DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_posts_created_id ON posts(id DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)")


def create_user(email: str, password_hash: str, display_name: str):
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email.strip().lower(), password_hash, display_name.strip()),
        )
        user_id = cursor.lastrowid
        db.execute("UPDATE users SET handle = ? WHERE id = ?", ("user" + str(user_id), user_id))
    return get_user(user_id)


def get_user_by_email(email: str):
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user(user_id: int):
    with connect() as db:
        row = db.execute(
            "SELECT id, email, display_name, handle, bio, email_verified, totp_enabled, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def save_conversation(user_message: str, assistant_message: str, user_id: int | None = None):
    with connect() as db:
        db.execute(
            "INSERT INTO conversations (user_id, user_message, assistant_message) VALUES (?, ?, ?)",
            (user_id, user_message, assistant_message),
        )


def list_conversations(limit: int = 50, user_id: int | None = None):
    with connect() as db:
        rows = db.execute(
            "SELECT id, user_message, assistant_message, created_at FROM conversations WHERE user_id IS ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_conversations(user_id: int | None = None):
    with connect() as db:
        db.execute("DELETE FROM conversations WHERE user_id IS ?", (user_id,))
