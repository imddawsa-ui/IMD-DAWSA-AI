# Cloudflare deployment foundation

This folder contains the first Cloudflare runtime foundation for IMD DAWSA AI.

- `worker.js`: health/readiness API only. Product API modules are deliberately not represented as complete.
- `schema.sql`: D1 baseline schema for the existing identity, chat, social, messaging, marketplace and notification data model.
- `wrangler.toml`: binding for the Cloudflare D1 database created for this project.

## Status
The Cloudflare Pages project and D1 database have been created. The Pages-to-GitHub integration returned a Cloudflare-side 401, so Git-based Pages deployment is not yet verified. This Worker is a separate API foundation and does not replace the existing FastAPI/Ollama local runtime.

Before public production use: implement and test authentication/session security, every API module, migrations, rate limiting, abuse controls, secrets, backups, monitoring and a full staging acceptance suite. Never point the production frontend at this foundation until its required endpoints are implemented.
