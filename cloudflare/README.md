# Cloudflare deployment foundation

This folder contains the first Cloudflare runtime foundation for IMD DAWSA AI.

- `worker.js`: health/readiness API only. Product API modules are deliberately not represented as complete.
- `schema.sql`: D1 baseline schema for the existing identity, chat, social, messaging, marketplace and notification data model.
- `wrangler.toml`: binding for the Cloudflare D1 database created for this project.

## Status
The Cloudflare Pages project and D1 database have been created. The Pages-to-GitHub integration returned a Cloudflare-side 401, so Git-based Pages deployment is not yet verified. This Worker is a separate API foundation and does not replace the existing FastAPI/Ollama local runtime.

Before public production use: implement and test authentication/session security, every API module, migrations, rate limiting, abuse controls, secrets, backups, monitoring and a full staging acceptance suite. Never point the production frontend at this foundation until its required endpoints are implemented.

## Live infrastructure status (2026-10-30)

- Cloudflare D1 database was created and the baseline schema in `schema.sql` was applied. The database currently has tables for users, conversations, posts, follows, likes, comments, direct messages, marketplace listings/enquiries, notifications and audit events.
- Worker `imd-dawsa-ai-api` was uploaded with a D1 binding. It currently implements only `GET /api/health` and `GET /api/readiness`; other API routes intentionally return HTTP 501.
- Workers.dev subdomain `imddawsa-ai` was created and the Worker subdomain enabled.
- Pages project `imd-dawsa-ai.pages.dev` exists but has no deployment yet. Connecting the Git repository failed with a Cloudflare Pages Git installation 401. Repair the integration or use direct static asset deployment.
- A live public endpoint request could not be made from the deployment execution environment due its outbound network policy. Do not claim external reachability until a browser/device smoke test succeeds.

The existing FastAPI backend remains the feature-complete prototype API; this Cloudflare foundation is infrastructure groundwork, not a replacement or a complete production migration.
