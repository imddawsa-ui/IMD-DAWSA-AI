# Engineering Standards

## 1. Engineering language

English is the mandatory language for all engineering artifacts in this repository.

This applies to:
- Source code, identifiers, class names, function names, variables and constants.
- Code comments, docstrings, TODOs, FIXME notes and inline technical explanations.
- API route names, request/response field names, database tables and columns.
- Logs, diagnostic messages, exceptions and developer-facing error messages.
- File names, directory names, environment variable names and configuration keys.
- Tests, fixtures, test names, commit messages, pull request titles and CI job names.
- Technical documentation, architecture decisions, changelogs and release notes.

Do not write Arabic (or other natural-language text) directly inside source code, comments, identifiers, technical logs, schema definitions or developer documentation.

## 2. Product localization is separate

End-user interface languages are product features, not programming languages.

All user-facing strings must be stored in explicit localization resources, keyed by stable identifiers. Keep the source implementation and keys in English. Supported locale resources may contain Arabic and other translated text.

- English (en) is the fallback locale.
- Arabic (ar) is an optional user-interface locale with RTL layout.
- Locale selection must not change source code, API contracts, database identifiers or developer tooling.
- Never mix translated text into business logic.
- Missing translations must fall back to English and must not break rendering.

## 3. Naming conventions

- Python: PEP 8, snake_case for functions and variables, PascalCase for classes.
- Kotlin: official Kotlin conventions, camelCase for functions/properties and PascalCase for types.
- Web: semantic HTML, accessible labels, descriptive camelCase JavaScript identifiers and kebab-case CSS classes.
- API: versioned, predictable REST paths and English JSON field names.
- SQL: lowercase snake_case identifiers and explicit migrations.
- Environment variables: uppercase SCREAMING_SNAKE_CASE.

## 4. Quality gates

Every change must:
1. Keep source and technical documentation in English.
2. Add or update tests for changed behavior.
3. Pass formatting, linting, static checks and automated tests applicable to the component.
4. Avoid secrets, credentials and personal data in source control.
5. Update the execution register with evidence and remaining limitations.

A successful CI run proves only the checks executed by that workflow. It does not prove production readiness or real-device behavior.

## 5. Pull requests and commits

Use concise English imperative commit messages, for example:
- feat(auth): add password reset flow
- fix(web): correct locale fallback
- test(api): cover session expiration
- docs: update deployment runbook

Keep changes focused and reviewable. Do not mark a feature complete until its required tests and verification gates pass.