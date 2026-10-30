import base64
import hashlib
import hmac
import io
import json
import secrets
import time
from html import escape
from urllib.parse import quote

import httpx
import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .auth import issue_access_token, read_access_token, verify_password
from .config import settings
from .database import connect, get_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["account-security"])


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,))
        db.execute(
            "INSERT INTO email_verification_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (_digest(token), user_id, int(time.time()) + settings.email_verification_ttl_seconds),
        )
    return token


async def send_verification_email(email: str, token: str) -> bool:
    if not settings.resend_api_key or not settings.email_from or not settings.api_public_url.startswith("https://"):
        return False
    verify_url = settings.api_public_url.rstrip("/") + "/api/auth/verify-email?token=" + quote(token)
    payload = {
        "from": settings.email_from,
        "to": [email],
        "subject": "Verify your IMD DAWSA AI email",
        "html": (
            "<p>Welcome to IMD DAWSA AI.</p>"
            "<p>Open this link to verify your email. The link expires in 15 minutes.</p>"
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
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT user_id FROM email_verification_tokens WHERE token_hash = ? AND expires_at > ?",
            (_digest(token), now),
        ).fetchone()
        if not row:
            return None
        db.execute("DELETE FROM email_verification_tokens WHERE token_hash = ?", (_digest(token),))
        db.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (row["user_id"],))
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
        raise HTTPException(status_code=503, detail="Unable to decrypt MFA secret; check AUTH_SECRET_KEY")


def _verified_user(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = read_access_token(authorization.split(" ", 1)[1])
    user = get_user(user_id) if user_id else None
    if not user or not user.get("email_verified"):
        raise HTTPException(status_code=401, detail="A verified account session is required")
    return user


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class TotpCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=16, pattern=r"^\d{6}$")


class DisableTotpRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=32)


class TwoFactorLoginRequest(BaseModel):
    challenge_token: str = Field(min_length=20, max_length=2000)
    code: str = Field(min_length=6, max_length=32)


def _new_challenge(user_id: int) -> str:
    nonce = secrets.token_urlsafe(24)
    expires = int(time.time()) + 300
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": user_id, "purpose": "2fa", "exp": expires, "nonce": nonce
    }, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(hmac.new(
        settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256
    ).digest()).decode().rstrip("=")
    with connect() as db:
        db.execute("DELETE FROM two_factor_challenges WHERE expires_at <= ?", (int(time.time()),))
        db.execute(
            "INSERT INTO two_factor_challenges (user_id, nonce_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, _digest(nonce), expires),
        )
    return payload + "." + signature


def _consume_challenge(token: str) -> int | None:
    try:
        payload, signature = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(
            settings.auth_secret_key.encode(), payload.encode(), hashlib.sha256
        ).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        user_id, nonce, expires = int(data["sub"]), str(data["nonce"]), int(data["exp"])
        if data.get("purpose") != "2fa" or expires <= int(time.time()):
            return None
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT id, user_id FROM two_factor_challenges WHERE nonce_hash = ? AND expires_at > ? AND used_at IS NULL",
            (_digest(nonce), int(time.time())),
        ).fetchone()
        if not row or int(row["user_id"]) != user_id:
            return None
        db.execute("UPDATE two_factor_challenges SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    return user_id


def _totp_counter(secret: str, code: str) -> int | None:
    totp = pyotp.TOTP(secret)
    now = time.time()
    counter = int(now // totp.interval)
    for candidate in (counter - 1, counter, counter + 1):
        if candidate > 0 and totp.verify(code, for_time=candidate * totp.interval):
            return candidate
    return None


def verify_totp_for_user(user_id: int, code: str, consume: bool = False) -> bool:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT totp_secret_enc, totp_enabled, totp_last_counter FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row or not row["totp_enabled"] or not row["totp_secret_enc"]:
            return False
        secret = _decrypt_secret(row["totp_secret_enc"])
        counter = _totp_counter(secret, code.strip())
        if counter is None or counter <= int(row["totp_last_counter"] or 0):
            return False
        if consume:
            db.execute("UPDATE users SET totp_last_counter = ? WHERE id = ?", (counter, user_id))
        return True


def verify_recovery_code(user_id: int, code: str) -> bool:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT id FROM two_factor_recovery_codes WHERE user_id = ? AND code_hash = ? AND used_at IS NULL",
            (user_id, _digest(code.strip())),
        ).fetchone()
        if not row:
            return False
        db.execute("UPDATE two_factor_recovery_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
        return True


@router.get("/verify-email", response_class=HTMLResponse)
async def verification_confirmation(token: str):
    if not token or len(token) > 200:
        raise HTTPException(status_code=400, detail="Invalid verification link")
    safe_token = escape(token, quote=True)
    return HTMLResponse(
        "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Verify IMD DAWSA AI email</title></head><body>"
        "<h2>Verify your email</h2><p>Press the button to confirm your email address.</p>"
        f"<button id='verify'>Verify email</button><p id='result'></p>"
        "<script>document.getElementById('verify').onclick=async()=>{"
        "const r=await fetch('/api/auth/verify-email',{method:'POST',headers:{'Content-Type':'application/json'},"
        f"body:JSON.stringify({{token:'{safe_token}'}})}});"
        "document.getElementById('result').textContent=r.ok?'Email verified. You can now sign in.':'Link invalid or expired.';"
        "};</script></body></html>"
    )


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    user_id = consume_verification_token(request.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Verification token is invalid, expired, or already used")
    return {"verified": True, "message": "Email address verified. You can now sign in."}


@router.post("/resend-verification")
async def resend_verification(email: str):
    user = get_user_by_email(email)
    if not user or user.get("email_verified"):
        return {"accepted": True, "message": "If verification is needed, an email will be sent."}
    token = create_verification_token(user["id"])
    try:
        sent = await send_verification_email(user["email"], token)
    except httpx.HTTPError:
        sent = False
    if not sent:
        raise HTTPException(status_code=503, detail="Secure email delivery is not configured or unavailable")
    return {"accepted": True, "message": "Verification email sent."}


@router.post("/2fa/setup")
async def setup_totp(authorization: str | None = Header(default=None)):
    user = _verified_user(authorization)
    secret = pyotp.random_base32()
    with connect() as db:
        db.execute(
            "UPDATE users SET totp_secret_enc = ?, totp_enabled = 0, totp_last_counter = 0 WHERE id = ?",
            (_encrypt_secret(secret), user["id"]),
        )
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
    user = _verified_user(authorization)
    with connect() as db:
        row = db.execute("SELECT totp_secret_enc FROM users WHERE id = ?", (user["id"],)).fetchone()
    if not row or not row["totp_secret_enc"]:
        raise HTTPException(status_code=409, detail="Start 2FA setup first")
    secret = _decrypt_secret(row["totp_secret_enc"])
    counter = _totp_counter(secret, request.code)
    if counter is None:
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    recovery_codes = [secrets.token_urlsafe(12) for _ in range(10)]
    with connect() as db:
        db.execute(
            "UPDATE users SET totp_enabled = 1, totp_last_counter = ? WHERE id = ?",
            (counter, user["id"]),
        )
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user["id"],))
        for code in recovery_codes:
            db.execute(
                "INSERT INTO two_factor_recovery_codes (user_id, code_hash) VALUES (?, ?)",
                (user["id"], _digest(code)),
            )
    return {
        "enabled": True,
        "recovery_codes": recovery_codes,
        "warning": "Store these codes securely. Each code works once and is shown only now.",
    }


@router.post("/2fa/disable")
async def disable_totp(request: DisableTotpRequest, authorization: str | None = Header(default=None)):
    user = _verified_user(authorization)
    record = get_user_by_email(user["email"])
    if not record or not verify_password(request.password, record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    valid = verify_totp_for_user(user["id"], request.code, consume=True)
    if not valid:
        valid = verify_recovery_code(user["id"], request.code)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid authenticator or recovery code")
    with connect() as db:
        db.execute(
            "UPDATE users SET totp_enabled = 0, totp_secret_enc = NULL, totp_last_counter = 0 WHERE id = ?",
            (user["id"],),
        )
        db.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user["id"],))
        db.execute("DELETE FROM two_factor_challenges WHERE user_id = ?", (user["id"],))
    return {"enabled": False}


@router.post("/2fa/login")
async def complete_2fa_login(request: TwoFactorLoginRequest):
    user_id = _consume_challenge(request.challenge_token)
    user = get_user(user_id) if user_id else None
    if not user or not user.get("email_verified") or not user.get("totp_enabled"):
        raise HTTPException(status_code=401, detail="Invalid, expired, or already used sign-in challenge")
    valid = verify_totp_for_user(user_id, request.code, consume=True)
    if not valid:
        valid = verify_recovery_code(user_id, request.code)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid authenticator or recovery code")
    return {"user": user, "access_token": issue_access_token(user_id), "token_type": "bearer"}
