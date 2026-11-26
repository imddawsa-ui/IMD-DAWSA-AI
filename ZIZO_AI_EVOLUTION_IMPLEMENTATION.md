# ZIZO AI Evolution — Integration Workstream

Status: integration branch created from `main`; no production deployment or data migration has been performed.

## Preservation rules
- Keep the existing `main` branch and the Apiway ZIZO AI preview unchanged.
- All integration work happens on `zizo-ai-evolution-integration` until reviewed and tested.
- Do not add secrets, provider keys, signing keys, user data, or database dumps to Git.
- Do not route public traffic to the current Cloudflare Worker: it implements health/readiness only and returns 501 for other API modules.
- Do not describe debug APKs or CI success as a signed production release or physical-device acceptance.

## Verified repository baseline
- FastAPI backend, SQLite persistence, Ollama local inference, optional OpenAI-compatible provider.
- Static Web/PWA client in `web/`.
- Native Android client in `android/`; separate Flutter client in `flutter_app/`.
- Authentication foundation includes email verification and optional TOTP MFA.
- Social foundation includes text posts, follows, likes, comments, notifications, and one-to-one text messages.
- Encrypted SQLite backup/verification utilities exist; scheduled backups and restore drills remain pending.
- GitHub Actions workflows validate backend, web assets, Android debug build, and Flutter build/tests.
- Cloudflare Worker currently exposes only `/api/health` and `/api/readiness`; other API routes return 501.

## Release blockers (must be closed before public multi-user launch)
1. Complete authentication lifecycle: password reset, token rotation/revocation, session/device management, recovery.
2. Prove per-user authorization for every private API resource.
3. Add distributed rate limiting, abuse/spam controls, request-size limits, validation, and safe error handling.
4. Replace single-host SQLite for multi-instance hosting; add schema migrations and tested managed-database backup/restore.
5. Implement production API modules before directing frontend traffic to Cloudflare.
6. Configure HTTPS, exact CORS origins, secure headers, secret storage/rotation, and CSRF strategy where applicable.
7. Add monitoring, alerting, audit/incident process, privacy/data deletion, terms, and moderation/report/block workflows.
8. Test accessibility, RTL, browsers, offline behavior, load, security, Android physical devices, and recovery.
9. Verify AI provider licensing, privacy, model availability, usage limits, and cost controls.

## Delivery sequence
### Phase A — Baseline and backup
- Record current `main` commit and workflow status.
- Verify source contains no credentials or private user data.
- Preserve current Apiway preview and GitHub main branch.

### Phase B — Feature parity and integration
- Map Apiway pages to FastAPI endpoints and Android/Web screens.
- Choose one canonical client for release; avoid maintaining duplicate feature implementations without a reason.
- Implement missing API contracts and UI flows incrementally with tests.

### Phase C — Security and data
- Close authentication and authorization blockers.
- Introduce database migrations and a managed database only after compatibility and rollback tests.
- Verify encrypted backups with a full restore drill.

### Phase D — Staging
- Deploy a non-production staging API and frontend only after secrets are configured in the host's secret manager.
- Keep AI local by default; enable cloud providers only through private server-side configuration.
- Run end-to-end tests on a physical Android device.

### Phase E — Release
- Publish static frontend separately from the API.
- Enable public API traffic only after every release blocker is verified.
- Produce a signed Android release only with a privately managed signing key.
- Record exact URLs, versions, test results, and rollback steps.

## Current decision
This branch is a safe integration workstream, not a completed migration. No public launch is approved by this document. Free tiers are quota-limited and may sleep or change; no paid resources are authorized.
