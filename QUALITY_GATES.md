# Release Quality Gates

## Release policy

No release may be described as production-ready until every applicable gate below has objective evidence. A green CI run is necessary but is not sufficient.

## Automated gates

- Python compilation and backend test suite pass.
- Web manifest parses and service-worker and inline JavaScript syntax checks pass.
- Android debug APK builds and the artifact is non-empty.
- Engineering language check passes; all temporary UI-localization exceptions are explicitly listed in `scripts/check_engineering_language.py`.
- Security-sensitive changes include regression tests.

## Integration and acceptance gates

- Authentication: registration, email verification, login, logout, expired sessions, MFA setup/disable, recovery and account recovery tested end to end.
- API: every documented route tested for authorization, validation, error handling, rate limits and data isolation.
- AI: local Ollama startup, model availability, timeout, offline behavior and CPU/RAM constraints tested on the target Windows machine.
- Translation: provider configured, supported language pairs queried from the engine, representative round-trip tests passed; no claim of universal language coverage.
- Web: production URL, HTTPS, browser console, PWA install, service-worker update and core user journeys tested.
- Android: install, launch, network configuration, authentication, chat, marketplace, localization, offline/error states and upgrade tested on a physical device.
- Data: migrations, backups, restore drill, deletion/export controls and multi-user isolation verified.
- Operations: production secrets, TLS, monitoring, alerting, abuse controls, dependency updates and incident/recovery runbook verified.

## Evidence and status

Use the status labels in `EXECUTION_REGISTER.md`. Record commit SHA, workflow run, test evidence, environment and known limitations. Mark a feature VERIFIED only after its relevant integration, device or deployment check succeeds.

## Release decision

A release is blocked if any critical security, data integrity, authentication, deployment or core user-journey gate is failing or unverified. Do not convert an unknown result into a pass. Do not claim 100% reliability; report the exact scope and evidence of verification.

## Current known limitations

- The repository's current CI checks syntax, backend tests and Android debug compilation; it is not a full end-to-end suite.
- `app/main.py`, `android/app/src/main/java/com/imddawsa/ai/MainActivity.kt`, `web/index.html` and `static/index.html` temporarily contain user-interface localization strings. These are explicitly allowlisted migration debt and must be moved into dedicated locale resources before the engineering-language gate can cover every source file.
- A debug APK build is not a signed production APK and does not prove physical-device compatibility.
- A Pages project without a successful deployment is not a live website.
- No public backend deployment or full production acceptance run is currently verified.