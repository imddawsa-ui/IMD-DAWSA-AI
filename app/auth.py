import base64
import hashlib
import hmac
import json
import secrets
import time

from .config import settings

_ITERATIONS = 310_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return str(_ITERATIONS) + "$" + _b64(salt) + "$" + _b64(digest)


def verify_password(password: str, encoded: str) -> bool:
    try:
        iterations, salt, expected = encoded.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt), int(iterations))
        return hmac.compare_digest(_b64(actual), expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: int) -> str:
    if not settings.auth_secret_key:
        raise RuntimeError("AUTH_SECRET_KEY must be configured before account login is enabled")
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + settings.auth_token_ttl_seconds}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256).digest())
    return payload + "." + signature


def read_access_token(token: str) -> int | None:
    if not settings.auth_secret_key:
        return None
    try:
        payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        if int(data["exp"]) <= int(time.time()):
            return None
        user_id = int(data["sub"])
        return user_id if user_id > 0 else None
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
