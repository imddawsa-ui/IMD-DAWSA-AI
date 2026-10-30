"""Generate strong local-only secrets without overwriting valid existing values."""
from __future__ import annotations

import secrets
from pathlib import Path

from cryptography.fernet import Fernet


def configure(path: str | Path = ".env") -> bool:
    env_path = Path(path)
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    values = {
        "AUTH_SECRET_KEY": secrets.token_urlsafe(48),
        "BACKUP_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
    }
    changed = False
    lines = content.splitlines()
    for name, generated in values.items():
        found = False
        for index, line in enumerate(lines):
            if line.startswith(name + "="):
                found = True
                current = line.split("=", 1)[1].strip()
                minimum = 32 if name == "AUTH_SECRET_KEY" else 40
                if len(current) < minimum:
                    lines[index] = f"{name}={generated}"
                    changed = True
                break
        if not found:
            lines.append(f"{name}={generated}")
            changed = True
    if changed:
        env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return changed


if __name__ == "__main__":
    changed = configure()
    print("Local security keys generated." if changed else "Existing local security keys preserved.")
