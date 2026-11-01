# Zero-cost-first platform execution plan

This document records the approved cost policy for IMD DAWSA AI. The goal is to keep development, local use, builds and the first public static website at zero subscription cost. "Free" means within each provider's current free quotas and terms; it does not mean unlimited capacity, guaranteed uptime, or a permanently free public AI service.

## Approved architecture

| Layer | Initial choice | Cost and limits |
|---|---|---|
| Source control | Existing public GitHub repository | Keep the current repository; use GitHub Actions for CI and APK/Web build artifacts within available quotas. |
| Public website | GitHub Pages | Static frontend only. Requires the repository owner to select GitHub Actions under Settings → Pages. No API, SQLite or AI model runs on Pages. |
| Android | Existing Android and Flutter clients | Build debug APKs with GitHub Actions. A distributable release requires a private signing key and a separate release validation process. |
| Personal AI inference | Ollama on the owner's own computer | No model API bill. Requires local hardware, disk space and the model download; CPU inference can be slow. Never expose the Ollama port publicly. |
| Personal/local backend | Existing FastAPI + SQLite | Keep local-first for personal use and development. SQLite is not the shared database for a multi-instance public service. |
| Public API | Not enabled yet | Evaluate a free-tier host only after checking sleep behavior, persistent disk, region, quotas, secrets, and data retention. Do not claim always-on availability. |
| Shared cloud database | Not provisioned yet | Do not create a database account or migrate private data until a selected provider, free-tier retention, region, backups and access controls have been verified. |
| Email | Optional | Account verification needs a verified sender and provider credentials. Until then, do not bypass verification or pretend email delivery works. |

## Delivery stages

### Stage 1 — free local product and build pipeline
- Preserve the existing FastAPI, SQLite, Ollama, Web/PWA, Android and Flutter foundations.
- Keep local AI mode usable without paid model APIs.
- Run Python tests, Web checks, Android build and Flutter analysis/tests/build in CI.
- Store APK and Web build outputs as workflow artifacts; note that artifacts expire according to GitHub retention.
- Verify installation and core flows on a physical Android device before calling the APK device-tested.

### Stage 2 — public static website
- Use GitHub Pages instead of the currently failing Cloudflare Git integration.
- The repository owner must set Settings → Pages → Build and deployment → Source: GitHub Actions.
- Run the existing "Deploy IMD DAWSA AI web client" workflow and use the exact deployment URL reported by GitHub.
- Until a secure API exists, clearly label account, messaging, social and cloud-AI features as unavailable in the public static deployment.

### Stage 3 — shared API and database
- First close authentication and authorization gaps: password recovery, session/token revocation and rotation, device/session controls, rate limits, abuse controls, strict CORS and per-user access checks.
- Select a free-tier API host and managed database only after verifying current terms, idle/sleep behavior, persistence, backups, restore and data residency.
- Add migrations and automated tests before moving any user data.
- Put secrets only in server-side secret settings. Never commit credentials or put provider keys in browser JavaScript or Android resources.

### Stage 4 — shared web and Android experience
- Both clients call one versioned API.
- Account identity, chat history and user preferences are server-authoritative and scoped to the authenticated user.
- Test offline/local mode separately from cloud sync; do not silently send local conversations to a cloud provider.
- Add voice, translation and image services only when a free local implementation or a verified no-cost quota is available.

## Explicit non-goals for a zero-cost release
- No promise of unlimited AI usage, permanent free hosting, always-on free API compute, or unlimited database storage.
- No paid plan, domain, email service, store publication, or paid API may be activated without separate owner approval.
- No public multi-user launch until security, backups, privacy, moderation and recovery requirements are met.

## Current blockers and owner actions
1. Enable GitHub Pages with GitHub Actions as the source in repository settings.
2. Install the generated debug APK on a physical Android phone and report any crash or connection issue.
3. Decide later whether a public API is necessary; personal local mode does not require a cloud database.
4. If public accounts are required, authorize a specific free-tier API/database provider after its current limits and data-retention terms have been reviewed.

## Verification references
- Repository: https://github.com/imddawsa-ui/IMD-DAWSA-AI
- CI workflow: .github/workflows/ci.yml
- Static Pages workflow: .github/workflows/pages.yml
- Deployment readiness: GLOBAL_DEPLOYMENT_READINESS.md
