# Web client and publishing

## What is included
- Responsive Arabic-first web client in `web/`.
- Installable PWA manifest and service worker for caching the web shell.
- GitHub Actions workflow at `.github/workflows/pages.yml` to publish the static client to GitHub Pages on changes to `web/**`.

## Important architecture distinction
GitHub Pages hosts only the static web client. It does **not** host the FastAPI backend, SQLite database or local Ollama model. The client must be configured with the HTTPS URL of a separately deployed backend. A locally running Ollama model remains on the computer that hosts Ollama; a public website cannot access a visitor's localhost model automatically.

## Enable GitHub Pages
1. Open repository Settings → Pages.
2. Under Build and deployment, choose **GitHub Actions** as the source.
3. Ensure the `github-pages` environment/deployment is allowed by repository policy.
4. Push a change under `web/` or manually run **Deploy IMD DAWSA AI web client** from Actions.
5. Open the Pages URL shown on the workflow deployment.

The workflow prepares deployment; this repository integration cannot change the Pages settings or create a domain/hosting account on the owner's behalf.

## Connect the web client to the API
- Deploy FastAPI on a trusted host with HTTPS.
- Set `CORS_ORIGINS` on the API to the exact GitHub Pages origin (for this repository normally `https://imddawsa-ui.github.io`).
- Set a strong `API_ACCESS_TOKEN` only for a private/single-user test; do not embed a shared production secret in a public browser app.
- Enter the backend base URL in the web client's connection field.
- For a multi-user public product, implement real accounts, per-user authorization, rate limits, abuse controls and managed secrets before launch. A single shared API token in browser code is not production authentication.

## Offline behavior
The service worker caches the web shell only. Chat requires a reachable backend. Offline AI requires the model runtime and model files on a machine/device that can run them; this PWA does not bundle a local language model.
