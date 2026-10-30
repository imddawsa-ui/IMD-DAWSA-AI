# IMD DAWSA AI

Privacy-first AI assistant and unified platform foundation for Windows 11, 8 GB RAM and CPU-only hardware. The repository is being expanded in verified milestones; it is not yet a production-ready Super App.

## Implemented foundation
- Arabic-first Web/PWA client and early Android network client.
- FastAPI service with local Ollama and optional OpenAI-compatible provider.
- SQLite persistence and health/readiness endpoints.
- Email/password registration API, PBKDF2 password hashing and signed expiring bearer sessions.
- User-scoped conversation history for authenticated accounts.
- Automated Python, Web and Android CI workflows.

## Account API
Configure a unique `AUTH_SECRET_KEY` of at least 32 characters in your local `.env` before enabling account endpoints. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env` or share its values. Account endpoints:
- `POST /api/auth/register` — `email`, `password` (10+ characters), `display_name`.
- `POST /api/auth/login` — returns a bearer access token.
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`.
- Authenticated chat and conversation endpoints use the same bearer header and isolate each user's history.

Tokens expire after `AUTH_TOKEN_TTL_SECONDS` (default 24 hours). This milestone does not yet include email verification, password reset, refresh-token rotation, OAuth, MFA, rate limiting or production-grade account recovery; do not expose account registration publicly until those controls and HTTPS deployment are completed.

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
Social network, messaging, marketplace, payments, trading execution, embedded apps, voice/video calls, enterprise workspaces, Windows Master Studio, on-device Android inference and external social publishing remain planned or in progress. External platform integrations require official APIs, approvals and user authorization. No placeholder is described as a completed integration.
