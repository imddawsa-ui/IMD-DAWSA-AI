# IMD DAWSA AI account authentication

The backend account flow supports verified email registration and optional TOTP multi-factor authentication.

## Required deployment configuration

Set these values in the backend environment or hosting secret manager:

- `AUTH_SECRET_KEY`: unique random secret, at least 32 characters. Keep it stable; it also encrypts stored TOTP secrets.
- `RESEND_API_KEY`: Resend API key with permission to send mail.
- `EMAIL_FROM`: sender address on a domain verified in Resend.
- `API_PUBLIC_URL`: public HTTPS origin of the FastAPI backend, without a trailing slash.
- `EMAIL_VERIFICATION_TTL_SECONDS`: optional, defaults to 900 seconds.

Example local secret generation:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit these values or send them in chat. The email adapter intentionally fails closed unless Resend and an HTTPS public API URL are configured. The sender domain must be verified in Resend before live email delivery works.

## Account lifecycle

1. `POST /api/auth/register` with `email`, `password` (10+ characters), and `display_name`.
2. The backend stores a hashed one-time verification token and sends a Resend email.
3. The email link opens `GET /api/auth/verify-email?token=...`. GET only displays a confirmation page; it does not consume the token, avoiding automatic mail-scanner activation.
4. The confirmation button submits `POST /api/auth/verify-email` with the token. Tokens expire and can be used once.
5. `POST /api/auth/login` issues a bearer token only after email verification.

If an email must be sent again, call `POST /api/auth/resend-verification?email=...`. Responses intentionally do not reveal whether an email address belongs to an account.

## TOTP multi-factor authentication

- Authenticated and email-verified user: `POST /api/auth/2fa/setup`. The response contains a QR PNG (base64), an `otpauth://` URI, and a setup secret. Keep the response private.
- Scan the QR code with Google Authenticator, Microsoft Authenticator, or another standards-compliant TOTP app.
- Confirm setup: `POST /api/auth/2fa/enable` with the current six-digit code. Ten recovery codes are returned once; store them safely.
- Login with MFA: `POST /api/auth/login` returns `requires_2fa` and a short-lived challenge instead of an access token. Complete with `POST /api/auth/2fa/login` using `challenge_token` and a TOTP or unused recovery code.
- Disable MFA: `POST /api/auth/2fa/disable` requires the account password and a current TOTP or unused recovery code.

TOTP secrets are encrypted at rest; recovery codes are hashed and single-use. Successful TOTP time steps and MFA challenges cannot be replayed. A failed code does not burn the login challenge, allowing a retry within its five-minute lifetime.

## Client integration

The Web PWA and Android client expose registration, login, email verification handoff, TOTP enrollment, and recovery-code display. Authenticated API calls must send:

```http
Authorization: Bearer <access_token>
```

The email verification link requires the backend to be reachable publicly over HTTPS. GitHub Pages is a static frontend host and cannot run this FastAPI backend.

## Production hardening still required

The current rate limiter is process-local. Before a multi-worker or public production launch, use a shared Redis/API-gateway limiter, add password reset and refresh-token/session revocation, monitoring/audit trails, secure database backups, and a tested key-rotation procedure. This starter is not a security certification.
