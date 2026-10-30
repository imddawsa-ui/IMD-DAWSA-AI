# Security baseline

## Implemented in the current starter

- Passwords are stored as PBKDF2-HMAC-SHA256 hashes, not plaintext.
- Account sessions use signed, expiring bearer tokens. Set a unique `AUTH_SECRET_KEY` with at least 32 characters before enabling accounts.
- When account authentication is enabled, chat and conversation history/deletion require a valid account session. Anonymous shared conversation history is retained only in local development when account auth is disabled.
- Social post comments respect public, followers-only and private post visibility.
- Basic in-process rate limits protect login, registration and chat endpoints.
- Responses include baseline browser security headers; HSTS is emitted only on HTTPS requests.
- SQLite foreign keys and per-user conversation scoping are enabled.
- New accounts must verify their email before receiving a session token. Verification links expire and are single-use; opening the link with a GET request does not consume it, to avoid mail-scanner prefetch.
- Resend is the email provider adapter. Registration fails closed unless `RESEND_API_KEY`, `EMAIL_FROM` and an HTTPS `API_PUBLIC_URL` are configured.
- TOTP MFA can be enrolled with an authenticator app using a QR code. TOTP secrets are encrypted at rest with a key derived from `AUTH_SECRET_KEY`; recovery codes are stored as hashes and are single-use.
- MFA login uses short-lived, signed, database-backed challenges. Valid TOTP time steps cannot be replayed, challenges are single-use after successful verification, and login/MFA endpoints have basic per-process rate limits.

## Required before public production launch

- Deploy only behind HTTPS/TLS. HSTS does not create HTTPS; configure TLS at the hosting gateway.
- Add a shared rate limiter (for example Redis or an API gateway). The current limiter is per process and is not sufficient across multiple workers or instances.
- Configure and verify a sender domain in Resend, then set `RESEND_API_KEY`, `EMAIL_FROM` and the public HTTPS `API_PUBLIC_URL` in the deployment secret manager. Do not put provider credentials in source control.
- Back up `AUTH_SECRET_KEY` securely: rotating it without a planned key migration invalidates existing sessions and prevents decrypting enrolled TOTP secrets.
- Add secure password reset, refresh-token rotation/revocation, account/device session management, MFA recovery workflows and administrator-assisted recovery.
- Add durable security audit events, alerting, abuse detection, and administrative RBAC.
- Add encrypted backups and a tested restore process. SQLite is not encrypted at rest by this starter.
- Configure a restrictive production CORS allowlist, WAF/DDoS protection, upload scanning, dependency scanning and secrets management.
- Add payment-provider webhooks and server-side transaction validation before enabling payments.
- Keep live trading disabled until broker authorization, explicit confirmations, risk limits and independent testing are implemented.

## Safe local setup

- Keep the service bound to `127.0.0.1` unless a secured deployment is configured.
- Never commit `.env`, SQLite databases, backups, access tokens or provider credentials.
- Generate a unique secret locally; do not send it in chat or commit it:
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- Put the generated value in your local `.env` as `AUTH_SECRET_KEY=...`.
- Use official OAuth flows for third-party integrations; never collect social-platform passwords.
- Treat model output and uploaded content as untrusted.

This document distinguishes implemented starter protections from production requirements. It is not a security certification.
