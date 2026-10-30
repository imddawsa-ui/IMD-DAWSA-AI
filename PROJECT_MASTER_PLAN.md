# IMD DAWSA AI — Master Project Blueprint

**Product identity:** IMD DAWSA AI  
**Project type:** Unified AI-powered platform and application ecosystem  
**Primary development target:** Windows 11, 8 GB RAM, CPU-only  
**Client targets:** Windows desktop, Android, Web  
**Languages:** Arabic and English first; architecture must support global localization, RTL/LTR, locale-aware dates, numbers, currencies and time zones.

## 1. Product vision and delivery rule

Build one coherent platform with a shared identity, backend, data model, permissions, AI services and design system. Windows Master Studio is the development/control workspace; it is not a substitute for the end-user Android, Windows and Web products.

No module is complete because a screen exists. Each capability needs working backend behavior, validation, authorization, error handling, tests, documentation and relevant real-device or deployment verification.

Lifecycle labels:
- **PLANNED** — scoped but not implemented.
- **IN_PROGRESS** — implementation underway.
- **IMPLEMENTED** — code exists, verification incomplete.
- **TESTED** — automated tests pass.
- **VERIFIED** — relevant real-device, integration or deployment check passes.
- **BLOCKED** — waiting on external credentials, approval, infrastructure, hardware or user action.

Never report a feature as ready based only on a mockup, placeholder, compile success or unverified integration.

## 2. Complete product map

### A. IMD Intelligence — AI core
- Provider-neutral model gateway and model registry.
- Local model provider for modest CPU-only Windows hardware; optional cloud providers.
- Conversation orchestration, system policies, context management and streaming.
- Personal memory with user controls; separate knowledge bases and retrieval (RAG).
- Tool calling and permissioned agent execution.
- Multi-agent task planning, delegation, progress tracking and resumable jobs.
- Web research and source attribution when online.
- File ingestion and document Q&A.
- Image understanding and generation integration.
- Speech-to-text, text-to-speech, voice conversations and translation.
- Coding assistant, project workspace and code review.
- Evaluation, feedback, safety checks and model/provider health.
- Explicit consent for any data used for improvement; no automatic training on private chats.
- Honest capability routing: local/offline vs online/cloud, with visible status and fallback behavior.

### B. Windows Master Studio
- Native-feeling Windows desktop control center.
- Project dashboard, module map, task queue, agent activity and logs.
- Requirements and architecture workspace.
- Code generation/editing with diff preview and approval gates for risky changes.
- Build, test, lint, dependency and security-check runners.
- Artifact management for Windows installers, Android APK/AAB and Web releases.
- Environment diagnostics, model manager, local service controls and backups.
- Safe terminal/task execution with scoped permissions and audit trail.
- No silent destructive actions, credential exposure or uncontrolled shell execution.

### C. Identity, accounts and profiles
- Email registration and verification; phone verification where an SMS provider is configured.
- Secure login, logout, session rotation, password reset and account recovery.
- Social sign-in through official OAuth where approved and configured (Facebook and X requested; Google/Apple can be added).
- User profiles, avatar, biography, privacy settings, language, country and preferences.
- Roles, permissions, account status, blocking and reporting.
- User data export, correction and deletion workflows.

### D. Social platform
- Home feed and discovery.
- Text, image, video and multi-media posts.
- Stories and short-form video/reels.
- Likes, comments, replies, shares, bookmarks and follows.
- Profiles, followers/following and creator pages.
- Direct messaging, group conversations and message requests.
- Groups, communities, channels, topics and events.
- Search, hashtags, mentions and notifications.
- Content privacy, audience controls, blocking, reporting and moderation.
- Upload pipeline, media processing, thumbnails, quotas and safe storage.

### E. Unified creator and publishing studio
- Drafts, media library, post composer, preview and scheduling.
- Publish to IMD first.
- Connect external accounts through official OAuth and supported APIs only.
- Requested destinations: Facebook, Instagram, X, YouTube and TikTok.
- Per-platform validation, permissions, media constraints and publishing status.
- Queue, retries, audit history and clear failure messages.
- Never promise or simulate publishing where an API/platform does not permit it; user approval required before external publication.

### F. Marketplace, business and services
- Product/service listings, categories, search and filters.
- Seller/business profiles, catalogues and storefronts.
- Enquiries, saved listings and order/request workflows.
- Pricing, currency localization, availability and location fields.
- Reviews, ratings, dispute/report workflows and trust indicators.
- Payment provider integration only after provider, country availability, compliance and credentials are confirmed.
- No storage of raw card details.

### G. Learning, work and creator tools
- Learning paths, lessons, resources, progress and assessments.
- Job and opportunity listings, applications and employer profiles.
- Creator workspace for content planning and analytics.
- Business workspace, team roles and collaboration.
- AI-assisted writing, translation, summarization and media preparation.

### H. Admin, trust and operations
- Admin dashboard with role-based access and audit logs.
- User, content, listing, report and appeal management.
- Moderation queues and configurable policy enforcement.
- Abuse prevention, rate limits, spam controls and account security.
- Operational metrics, service health, error tracking and incident records.
- Feature flags, configuration and release management.

### I. Platform foundation
- API contracts and versioning.
- Database schema, migrations, tenant/user isolation.
- SQLite for local development; production relational database such as PostgreSQL.
- Background jobs and queues for media, notifications, publishing and AI tasks.
- Object storage for uploaded media and generated artifacts.
- Cache and search infrastructure when scale requires it.
- Secure secrets management, encryption in transit/at rest, backups and recovery.
- Observability, structured logs and privacy-aware analytics.
- CI checks, reproducible builds, dependency pinning and release artifacts.

## 3. Shared architecture

- **Clients:** Windows Master Studio, Android app and responsive Web app.
- **Backend:** versioned API and service modules with centralized identity and authorization.
- **AI layer:** provider adapters, model routing, agent runtime, memory, retrieval and evaluations.
- **Data:** relational records, media/object storage, search index and background-job state.
- **Integrations:** official OAuth/API adapters behind explicit scopes and feature flags.
- **Operations:** CI/CD, telemetry, audit, backups, deployment and incident response.

Avoid tightly coupling UI code to one AI vendor or one client. Shared business rules belong in the backend or shared domain layer.

## 4. Delivery phases and dependencies

| Phase | Scope | Exit criteria |
|---|---|---|
| 0 — Baseline and governance | Inventory, requirements, architecture, threat model, CI, status register | Scope map and acceptance criteria committed |
| 1 — Reliable core | API, configuration, persistence, health/readiness, provider gateway, error handling | Unit/API tests pass; clean Windows setup documented |
| 2 — Windows Master Studio | Desktop shell, project control, logs, safe task runner, build/test controls | Windows build and smoke test verified |
| 3 — AI capabilities | Local model, optional cloud routing, chat, memory, files, RAG, tools/agents | Offline and online behavior tested separately |
| 4 — Identity and localization | Accounts, sessions, verification adapters, profiles, roles, RTL/LTR | Auth/security tests and localization checks pass |
| 5 — Social foundation | Profiles, posts, feed, follows, comments, reactions, media | End-to-end social flows tested |
| 6 — Messaging and communities | DMs, groups, channels, events, notifications, search | Multi-user integration tests pass |
| 7 — Marketplace and work | Listings, business pages, orders/requests, learning, jobs, creator tools | Permission, workflow and abuse tests pass |
| 8 — Publisher and integrations | Drafts, scheduling, official platform OAuth/API adapters | Each platform integration independently verified |
| 9 — Admin, safety and scale | Moderation, audit, analytics, rate limits, storage, jobs, backups | Security review and recovery tests pass |
| 10 — Client releases | Android, Web and Windows packaging and distribution | Signed builds, device/browser matrix and release checklist pass |
| 11 — Production operations | Deployment, monitoring, support, incident and upgrade procedures | Staging and production acceptance checks pass |

Phases may overlap only where dependencies are satisfied. A feature blocked by a third-party API must remain visibly BLOCKED rather than be represented by a fake working integration.

## 5. Windows 11 / 8 GB / CPU-only constraints

- Keep the development toolchain and default local model lightweight.
- Start with a small quantized model and allow model selection based on measured RAM.
- Do not load multiple large models simultaneously on the target machine.
- Treat image generation, large multimodal models and heavy training as optional cloud/remote workloads unless actual hardware benchmarks prove local feasibility.
- Model download requires internet; offline inference is possible only after model/runtime installation and a successful offline test.
- Android network access to a Windows-hosted API is not the same as on-device offline AI. These must be tested and described separately.

## 6. Security and privacy gates

- No production exposure of development endpoints.
- HTTPS/TLS, secure authentication, authorization on every user-owned resource and rate limiting before public launch.
- Store secrets only in environment/secret managers; never commit keys or tokens.
- OAuth state/PKCE and least-privilege scopes where supported.
- Validate uploads, file types, size, content and ownership.
- Audit privileged actions; protect admin routes.
- Separate private user memory from shared/global knowledge.
- Explicit consent, retention controls and deletion/export paths.
- Backups must be encrypted and restore-tested.

## 7. Definition of done — applies to every feature

1. Requirement and user flow documented.
2. UI and API behavior implemented; no dead buttons or demo-only success states.
3. Authentication, authorization, validation and error states handled.
4. Unit and integration tests added and passing.
5. Accessibility, localization and RTL/LTR checked where applicable.
6. Security/privacy implications reviewed.
7. Logs and operational behavior are observable without leaking secrets.
8. Documentation and setup instructions updated.
9. CI build succeeds.
10. Relevant real device, external integration or deployment smoke test passes.
11. Status advanced to TESTED or VERIFIED only with evidence.

## 8. Current repository baseline (2026-10-30)

The repository currently contains an early FastAPI/Ollama foundation, SQLite conversation storage, a basic web UI, Windows batch scripts, an early Android network client and GitHub Actions CI. The current Android client is not independently offline-capable. There is not yet a complete production identity system, full social platform, marketplace, messaging, official external publishing integrations, production deployment or finished Windows Master Studio.

The latest recorded CI run at commit 298b8ca8d099a8953a6b2fd974cbc15ca1ddd21c completed successfully. This confirms that the configured CI jobs passed for that commit; it does not mean the product is complete or production-ready.

## 9. Execution register

Maintain a living module register in the repository. For every feature record:
- owner/module;
- lifecycle status;
- implementation paths;
- tests and latest result;
- known gaps;
- external dependency or approval;
- next concrete action.

Work in a strict loop: inspect → implement the smallest coherent slice → test → document → update status. Keep a visible BLOCKED list and do not silently drop requirements.

## 10. Explicit non-goals and honest limits

- Do not claim to create a frontier-scale foundation model from scratch on an 8 GB CPU-only laptop. Integrate existing models first; evaluate fine-tuning only when data, compute, rights and safety controls exist.
- Do not bypass third-party platform restrictions or automate account access outside official supported APIs.
- Do not mark external services as connected without successful OAuth/API verification.
- Do not claim full offline capability until the exact workflow succeeds with networking disabled.
- Do not claim complete release readiness until security, device, integration and deployment acceptance checks pass.
