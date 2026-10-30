# IMD DAWSA AI

Privacy-first AI assistant and unified platform foundation for Windows 11, 8 GB RAM and CPU-only hardware. The repository is being expanded in verified milestones; it is not yet a production-ready Super App.

## Implemented foundation
- Arabic-first Web/PWA client and early Android network client.
- FastAPI service with local Ollama and optional OpenAI-compatible provider.
- SQLite persistence and health/readiness endpoints.
- Email/password registration with Resend email verification, PBKDF2 password hashing and signed expiring bearer sessions.
- Optional TOTP multi-factor authentication, encrypted authenticator secrets and one-time recovery codes.
- Social profiles, public/follower/private text posts, feed, follows, likes and comments.
- Authenticated one-to-one private messaging API.
- Marketplace seller dashboard APIs for owned listings and buyer enquiries, with a basic Web seller inbox.
- User-scoped conversation history for authenticated accounts.
- Recent conversation context (up to eight prior turns) supplied to local and cloud models.
- Automated Python, Web and Android CI workflows.

## Account and security setup
Configure a unique `AUTH_SECRET_KEY` (at least 32 characters), `RESEND_API_KEY`, `EMAIL_FROM` on a verified Resend sender domain, and a public HTTPS `API_PUBLIC_URL` in the backend environment. Generate the signing key locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env` or share its values. New accounts must verify email before login. See [AUTHENTICATION.md](AUTHENTICATION.md) for the full lifecycle and TOTP setup. Tokens expire after `AUTH_TOKEN_TTL_SECONDS` (default 24 hours). Configure `CORS_ORIGINS` with the exact deployed frontend origin.

Account endpoints:
- `POST /api/auth/register` — `email`, `password` (10+ characters), `display_name`.
- `POST /api/auth/verify-email` — consume a one-time email verification token.
- `POST /api/auth/login` — returns a bearer token or an MFA challenge.
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`.
- `POST /api/auth/2fa/setup`, `/enable`, `/login`, `/disable` — TOTP MFA lifecycle.
- Authenticated chat, social, messaging and conversation endpoints require the bearer header when account security is enabled.

Social API:
- `GET /api/social/feed`, `GET /api/social/users/{id}`, `PATCH /api/social/profile`.
- `POST /api/social/posts`, `POST /api/social/users/{id}/follow`, `DELETE /api/social/users/{id}/follow`.
- `POST /api/social/posts/{id}/like`, `POST/GET /api/social/posts/{id}/comments`.
- `POST/GET /api/social/messages/{user_id}` — participant-scoped private direct messages.

The current authentication and messaging foundation is not a complete production identity platform: password reset, refresh-token rotation/revocation, device/session management and shared distributed abuse controls remain required.

## Windows setup
1. Install Python 3.11+ and Ollama.
2. Copy `.env.example` to `.env`; generate and set `AUTH_SECRET_KEY` locally.
3. Run `install_windows.bat`.
4. Run `pull_model.bat` once (model download requires internet).
5. Run `start_windows.bat` and open http://127.0.0.1:8000.

After the model is downloaded, local chat can run offline. Account sessions are local to the configured backend/database.

## API and deployment
- `GET /api/health`, `GET /api/readiness`, `POST /api/chat`.
- Read [SECURITY.md](SECURITY.md), [ROADMAP.md](ROADMAP.md) and [EXECUTION_REGISTER.md](EXECUTION_REGISTER.md).
- The Web client in `web/` is static. GitHub Pages does not host FastAPI, SQLite or Ollama. Enable Pages using **Settings → Pages → Build and deployment → GitHub Actions**, then deploy a separate HTTPS backend and set its exact origin in `CORS_ORIGINS`. See [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md).

## Product status
Marketplace, payments, trading execution, embedded apps, voice/video calls, enterprise workspaces, Windows Master Studio, on-device Android inference and external social publishing remain planned or in progress. Social features currently cover text posts, follows, likes, comments and one-to-one text messaging only. External platform integrations require official APIs, approvals and user authorization. No placeholder is described as a completed integration.
