# IMD DAWSA AI — delivery roadmap

## 0.1 Local assistant foundation
FastAPI service, Arabic web UI, Ollama chat, SQLite history and health checks.

## 0.2 API foundation (in progress)
Conversation history and deletion endpoints, selectable local Ollama or OpenAI-compatible cloud provider, API tests and Android client build pipeline.

## 0.3 Android client
Native Android application connected to the FastAPI service. Current client is an early network client; it is not yet an independently offline-capable on-device model app.

## 0.4 True on-device AI and offline mode
Integrate a quantized mobile model runtime, model download/verification, device capability checks, local encrypted storage and explicit model lifecycle controls. Must be validated on actual target phones before claiming offline inference.

## 0.5 Accounts and sync
Email verification, secure sessions, PostgreSQL migrations, user-scoped data, opt-in sync, backup/restore and privacy controls.

## 0.6 Super App modules
Profiles, posts, feed, messaging, groups, notifications, marketplace, business pages, learning, creator tools, moderation and admin audit logs.

## 0.7 Integrations and production
Official OAuth/API integrations, background jobs, object storage, observability, rate limits, security review, deployment and store release.

A milestone is complete only after implementation, automated tests, security checks and a real device/deployment check. This project integrates existing models; it does not train a frontier model from scratch. Do not expose the development API publicly without HTTPS, authentication, rate limiting and production hardening.


## Master project governance

The complete product scope, architecture, delivery phases, hardware constraints and definition of done are maintained in [PROJECT_MASTER_PLAN.md](PROJECT_MASTER_PLAN.md).

Evidence-based module status and external blockers are tracked in [EXECUTION_REGISTER.md](EXECUTION_REGISTER.md). Keep both files updated as implementation advances; do not silently drop a requested module or mark unverified work complete.
