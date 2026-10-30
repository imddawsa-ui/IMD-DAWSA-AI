from pathlib import Path

from cryptography.fernet import Fernet

from scripts.configure_local import configure


def test_configure_generates_auth_and_backup_keys(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("APP_NAME=NILE ONE HUMAN\nAUTH_SECRET_KEY=\nBACKUP_ENCRYPTION_KEY=\n", encoding="utf-8")

    assert configure(env) is True

    values = dict(line.split("=", 1) for line in env.read_text(encoding="utf-8").splitlines() if "=" in line)
    assert len(values["AUTH_SECRET_KEY"]) >= 32
    assert Fernet(values["BACKUP_ENCRYPTION_KEY"].encode("ascii"))


def test_configure_preserves_existing_valid_keys(tmp_path: Path):
    env = tmp_path / ".env"
    auth_key = "a" * 48
    backup_key = Fernet.generate_key().decode("ascii")
    env.write_text(
        f"AUTH_SECRET_KEY={auth_key}\nBACKUP_ENCRYPTION_KEY={backup_key}\n",
        encoding="utf-8",
    )

    assert configure(env) is False
    values = dict(line.split("=", 1) for line in env.read_text(encoding="utf-8").splitlines())
    assert values["AUTH_SECRET_KEY"] == auth_key
    assert values["BACKUP_ENCRYPTION_KEY"] == backup_key
