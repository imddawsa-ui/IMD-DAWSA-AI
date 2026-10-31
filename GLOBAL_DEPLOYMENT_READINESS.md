# Global public deployment readiness

Last reviewed: 2026-10-31

## Current verified position

- The GitHub repository is public and its CI workflow builds the Web client, Android debug APK and Flutter Web release.
- `.github/workflows/pages.yml` is configured to publish the static `web/` directory to GitHub Pages when Pages is enabled with **GitHub Actions** as the source.
- A Cloudflare Pages project named `imd-dawsa-ai` exists at `imd-dawsa-ai.pages.dev`, but the Cloudflare account reports no deployment yet.
- The Cloudflare Worker foundation implements health/readiness only. It is not the production API and must not receive public user traffic.
- The FastAPI + SQLite + Ollama service is a local-first prototype. GitHub Pages and Cloudflare Pages do not run that service or host its SQLite database/model.

## Zero-cost-first target architecture

1. Static frontend: GitHub Pages (first deployment path; no paid domain required) or the existing Cloudflare Pages project.
2. API: keep the current FastAPI service local until a secure, always-on backend host has been selected and tested. A free-tier backend may be evaluated, but availability, sleeping, quotas, region and data retention must be checked at launch time.
3. AI inference: Ollama on the user's own computer for private/local mode. Do not route public visitors to a developer's localhost or expose Ollama directly.
4. Database: SQLite is suitable for a single-host prototype only. A multi-user public service needs a managed database, migrations, backups and tested restore.
5. Secrets: backend-only environment variables/secret manager. Never place provider keys, signing secrets or a shared API token in browser JavaScript, Android resources or public artifacts.

## Owner actions required to publish the static site

1. Open repository Settings → Pages.
2. Set Build and deployment source to **GitHub Actions**.
3. Run the **Deploy IMD DAWSA AI web client** workflow, or push a change under `web/`.
4. Confirm the deployment job succeeds and open the exact URL shown in its deployment environment.
5. Test the deployed site from a phone and a desktop browser, including RTL layout, PWA install prompt, service-worker update and refresh/deep-link behavior.

Repository: https://github.com/imddawsa-ui/IMD-DAWSA-AI
Expected GitHub Pages origin for this owner/repository: https://imddawsa-ui.github.io
The actual URL must be taken from the successful deployment, not assumed.

## Production API release blockers

Do not advertise the public product as production-ready until all items below are implemented and independently verified:

- Complete production authentication lifecycle: password reset, refresh-token rotation/revocation, session/device management, email verification and recovery.
- Per-user authorization on every private resource; no shared browser-side API secret.
- Rate limiting, abuse/spam controls, account enumeration protection, input validation, request size limits and safe error handling.
- HTTPS-only API, exact CORS allowlist, secure headers, CSRF strategy where cookies are used, and secret rotation.
- Managed multi-user database with schema migrations, automated backups, restore drills and retention policy.
- Monitoring, alerting, audit logs, incident response and privacy/data deletion process.
- Terms of service, privacy notice, community guidelines, moderation/report/block workflows and contact channel.
- Load, security, accessibility, browser, Android physical-device and recovery testing.
- Explicit AI provider/model licensing, usage limits, privacy disclosures and cost controls.

## Owner approval and account-dependent items

No paid plan, domain purchase, subscription, app-store publication, public data migration or public API exposure is authorized by this preparation.

The owner must approve/provide only when ready:
- GitHub Pages setting change (repository owner action).
- Choice and authorization of the public API hosting account; verify free-tier limits and data location.
- A verified email sender/domain and Resend credentials if email verification is to be enabled.
- A domain name and DNS access only if a custom domain is wanted.
- Production secrets generated privately by the owner and entered directly into the chosen host's secret settings; never paste them into chat.
- Android release signing keystore and credentials only if distributing a signed release APK outside debug testing or publishing to an app store.

## Launch decision

Current status: **prepared for a static-site deployment, not approved for a public multi-user AI service**. A static website can be public before the API, but account, messaging, social and AI features must be clearly marked unavailable until a secured production API is deployed and tested.
