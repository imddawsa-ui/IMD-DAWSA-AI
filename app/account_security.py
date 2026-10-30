import base64
import hashlib
import hmac
import io
import json
import secrets
import time
from urllib.parse import quote

import httpx
import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .config import settings
from .database import connect, get_user
from .auth import issue_access_token

router = APIRouter(prefix="/api/auth", tags=["account-security"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,))
        db.execute(
            "INSERT INTO email_verification_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, _token_hash(token), int(time.time()) + settings.email_verification_ttl_seconds),
        )
    return token


async def send_verification_email(email: str, token: str) -> bool:
    if not settings.resend_api_key or not settings.email_from:
        return False
    verify_url = settings.api_public_url.rstrip("/") + "/api/auth/verify-email?token=" + quote(token)
    payload = {
        "from": settings.email_from,
        "to": [email],
        "subject": "Verify your IMD DAWSA AI email",
        "html": (
            "<p>Welcome to IMD DAWSA AI.</p>"
            "<p>Confirm your email address using the secure link below. It expires soon.</p>"
            f'<p><a href="{verify_url}">Verify email address</a></p>'
            "<p>If you did not create this account, ignore this message.</p>"
        ),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": "Bearer " + settings.resend_api_key},
        )
        response.raise_for_status()
    return True


def consume_verification_token(token: str) -> int | None:
    if not token or len(token) > 200:
        return None
    now = int(time.time())
    with connect() as db:
        row = db.execute(
            "SELECT id, user_id FROM email_verification_tokens WHERE token_hash = ? AND expires_at > ?",
            (_token_hash(token), now),
        ).fetchone()
        if not row:
            return None
        db.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (row["user_id"],))
        db.execute("DELETE FROM email_verification_tokens WHERE user_id = ?", (row["user_id"],))
        return int(row["user_id"])


def _fernet() -> Fernet:
    if len(settings.auth_secret_key) < 32:
        raise RuntimeError("AUTH_SECRET_KEY must contain at least 32 characters")
    key = base64.urlsafe_b64encode(hashlib.sha256(
        b"imd-dawsa-totp-encryption:" + settings.auth_secret_key.encode("utf-8")
    ).digest())
    return Fernet(key)


def _encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        raise HTTPException(status_code=503, detail="Unable to decrypt MFA secret; rotate security configuration")


def verify_totp_for_user(user_id: int, code: str) -> bool:
    with connect() as db:
        row = db.execute("SELECT totp_secret_enc, totp_enabled FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or not row["totp_enabled"] or not row["totp_secret_enc"]:
        return False
    secret = _decrypt_secret(row["totp_secret_enc"])
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class TotpCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=16)


class DisableTotpRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=32)


def _authenticated_user(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    from .auth import read_access_token
    user_id = read_access_token(authorization.split(" ", 1)[1])
    user = get_user(user_id) if user_id else None
    if not user or not user.get("email_verified"):
        raise HTTPException(status_code=401, detail="A verified account session is required")
    return user


@router.get("/verify-email")
async def verify_email_link(token: str):
    user_id = consume_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
    return {"verified": True, "message": "Email address verified. You can now sign in."}


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    user_id = consume_verification_token(request.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")
    return {"verified": True, "message": "Email address verified. You can now sign in."}


@router.post("/resend-verification")
async def resend_verification(email: str):
    from .database import get_user_by_email
    user = get_user_by_email(email)
    # Same response for unknown and already verified addresses to reduce account enumeration.
    if not user or user.get("email_verified"):
        return {"accepted": True, "message": "If verification is needed, an email will be sent."}
    token = create_verification_token(user["id"])
    try:
        sent = await send_verification_email(user["email"], token)
    except httpx.HTTPError:
        sent = False
    if not sent:
        raise HTTPException(status_code=503, detail="Email delivery is not configured or temporarily unavailable")
    return {"accepted": True, "message": "Verification email sent."}


@router.post("/2fa/setup")
async def setup_totp(authorization: str | None = Header(default=None)):
    user = _authenticated_user(authorization)
    secret = pyotp.random_base32()
    with connect() as db:
        db.execute("UPDATE users SET totp_secret_enc = ?, totp_enabled = 0 WHERE id = ?",
                   (_encrypt_secret(secret), user["id"]))
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user["id"],))
    uri = pyotp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="IMD DAWSA AI")
    qr = qrcode.make(uri)
    output = io.BytesIO()
    qr.save(output, format="PNG")
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_code_png_base64": base64.b64encode(output.getvalue()).decode("ascii"),
        "message": "Scan the QR code, then confirm with a current 6-digit code.",
    }


@router.post("/2fa/enable")
async def enable_totp(request: TotpCodeRequest, authorization: str | None = Header(default=None)):
    user = _authenticated_user(authorization)
    with connect() as db:
        row = db.execute("SELECT totp_secret_enc FROM users WHERE id = ?", (user["id"],)).fetchone()
    if not row or not row["totp_secret_enc"]:
        raise HTTPException(status_code=409, detail="Start 2FA setup first")
    secret = _decrypt_secret(row["totp_secret_enc"])
    if not pyotp.TOTP(secret).verify(request.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    recovery_codes = [secrets.token_urlsafe(9) for _ in range(8)]
    with connect() as db:
        db.execute("UPDATE users SET totp_enabled = 1 WHERE id = ?", (user["id"],))
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user["id"],))
        for code in recovery_codes:
            db.execute("INSERT INTO two_factor_recovery_codes (user_id, code_hash) VALUES (?, ?)",
                       (user["id"], _token_hash(code)))
    return {"enabled": True, "recovery_codes": recovery_codes,
            "warning": "Save these recovery codes securely. They are shown only once."}


@router.post("/2fa/disable")
async def disable_totp(request: DisableTotpRequest, authorization: str | None = Header(default=None)):
    from .auth import verify_password
    user = _authenticated_user(authorization)
    from .database import get_user_by_email
    record = get_user_by_email(user["email"])
    if not record or not verify_password(request.password, record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    valid = verify_totp_for_user(user["id"], request.code)
    if not valid:
        digest = _token_hash(request.code.strip())
        with connect() as db:
            row = db.execute(
                "SELECT id FROM two_factor_recovery_codes WHERE user_id = ? AND code_hash = ? AND used_at IS NULL",
                (user["id"], digest),
            ).fetchone()
            if row:
                db.execute("UPDATE two_factor_recovery_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
                valid = True
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid authenticator or recovery code")
    with connect() as db:
        db.execute("UPDATE users SET totp_enabled = 0, totp_secret_enc = NULL WHERE id = ?", (user["id"],))
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user["id"],))
    return {"enabled": False}


def verify_recovery_code(user_id: int, code: str) -> bool:
    digest = _token_hash(code.strip())
    with connect() as db:
        row = db.execute(
            "SELECT id FROM two_factor_recovery_codes WHERE user_id = ? AND code_hash = ? AND used_at IS NULL",
            (user_id, digest),
        ).fetchone()
        if not row:
            return False
        db.execute("UPDATE two_factor_recovery_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    return True


class TwoFactorLoginRequest(BaseModel):
    challenge_token: str = Field(min_length=20, max_length=2000)
    code: str = Field(min_length=6, max_length=32)


def issue_2fa_challenge(user_id: int) -> str:
    import json
    import hmac
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": user_id, "purpose": "2fa", "exp": int(time.time()) + 300
    }, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(hmac.new(
        settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256
    ).digest()).decode().rstrip("=")
    return payload + "." + signature


def read_2fa_challenge(token: str) -> int | None:
    import json
    import hmac
    try:
        payload, signature = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(
            settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256
        ).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data.get("purpose") != "2fa" or int(data["exp"]) <= int(time.time()):
            return None
        return int(data["sub"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


@router.post("/2fa/login")
async def complete_2fa_login(request: TwoFactorLoginRequest):
    user_id = read_2fa_challenge(request.challenge_token)
    user = get_user(user_id) if user_id else None
    if not user or not user.get("email_verified") or not user.get("totp_enabled"):
        raise HTTPException(status_code=401, detail="Invalid or expired sign-in challenge")
    valid = verify_totp_for_user(user_id, request.code)
    if not valid:
        valid = verify_recovery_code(user_id, request.code)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid authenticator or recovery code")
    return {"user": user, "access_token": issue_access_token(user_id), "token_type": "bearer"}
