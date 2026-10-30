# NILE ONE HUMAN — Zero-Cost Deployment and Operation

**Budget target: USD 0.** This plan uses local-first operation and free/open-source software. It does not assume that any third-party free tier is permanent or sufficient for production.

## 1. Guaranteed zero-subscription baseline

Run the backend, SQLite database, Web client and local model on the user's own Windows 11 computer.

Requirements:
- Windows 11, Python 3.11+, Git and Ollama.
- 8 GB RAM, CPU-only: use a small quantized model such as Qwen 2.5 3B only after checking available RAM and disk. Close other heavy applications. Do not promise fast generation.
- Download the model once while online; local inference can then work offline.
- SQLite database and encrypted backups remain on the local device.
- Web UI is served by the local FastAPI process.
- Android APK can be built with the free Android/Gradle toolchain; local-network use requires the phone and computer to share a trusted Wi-Fi network and a correctly configured backend URL.

## 2. Free/open-source software choices

| Need | Zero-cost choice | Important limitation |
|---|---|---|
| Local AI inference | Ollama | Model downloads require internet and disk; CPU speed varies. |
| API backend | Python + FastAPI | User must run and maintain the process. |
| Local database | SQLite | Single-host database; not a managed multi-region database. |
| Web UI | Existing HTML/CSS/JS PWA | Local mode works without public hosting; remote access needs secure hosting/network. |
| Android build | Android SDK + Gradle | Debug APK is not a signed Play Store release. |
| Translation | Self-hosted LibreTranslate-compatible engine | Must install a compatible model/provider; language coverage varies. |
| Backups | Encrypted local SQLite backup | User must keep a separate safe copy; restore drills are required. |
| Source control and CI | GitHub free capabilities | Quotas and product terms can change; CI is not a production server. |

## 3. Public access without paying

A free public website/backend is not guaranteed. Use these options in order:
1. Local-only operation as the dependable zero-cost baseline.
2. A free static frontend host only for the static Web assets; it cannot run FastAPI, Ollama or SQLite.
3. A free backend/database tier only after verifying current limits, sleep behavior, data retention, region availability and terms. Never store critical user data until backups and restore are proven.
4. Do not depend on a free tunnel as a permanent production service. Never expose an unauthenticated local development server to the public internet.

No paid account, subscription, domain or cloud resource should be created by this project without explicit approval.

## 4. Privacy and security defaults

- Keep HOST=127.0.0.1 for local-only use.
- Generate AUTH_SECRET_KEY locally and keep it only in .env.
- Never commit .env, API keys, signing keys or backup encryption keys.
- Enable account email verification only after a real sender is configured. For a no-email local setup, document the supported local development flow without weakening production authentication.
- Encrypt backups; keep encryption keys separate from backup files.
- Do not claim end-to-end encryption unless it is implemented and independently tested.
- Do not expose admin, database, model or diagnostic endpoints publicly without authentication and authorization.

## 5. Android zero-cost path

- Build and install a debug APK for personal testing.
- Configure the backend URL to the computer's private LAN address only on a trusted network; do not hardcode a public IP.
- Test login, chat, offline/error states, permissions, RTL, and network loss on a physical phone.
- A Play Store release may require signing, account eligibility and fees; do not promise Play Store publication for zero cost. Direct APK distribution is possible but requires safe signing and user trust.

## 6. Release gate

A zero-cost build is called usable only after:
- backend and Web tests pass on the exact commit;
- Android debug APK builds and installs;
- the actual target phone can connect to the backend;
- local model inference is measured on the target PC;
- translation provider coverage is tested for the advertised languages;
- backup integrity and a full restore drill succeed;
- secrets are absent from source, logs and artifacts;
- offline behavior is tested with network disabled.

## 7. What zero cost cannot guarantee

No guaranteed always-on public server, custom domain, unlimited model inference, unlimited translation, paid SMS/email delivery, Play Store account, or production-grade cloud database is included. The product must remain useful in local-first mode without these services.