# Security notes

- Keep the service bound to 127.0.0.1 unless HTTPS, authentication and firewall rules are configured.
- Never commit .env, SQLite databases, backups, access tokens or provider credentials.
- Set a long random API_ACCESS_TOKEN before exposing API endpoints beyond localhost.
- Raw password storage and user account management are not implemented in milestone 0.1.
- Treat model output and uploaded content as untrusted.
- Use official OAuth flows for third-party integrations; never collect platform passwords.
- Add rate limiting, CSRF protections where applicable, audit logging, backups and dependency scanning before production.
- Local Ollama mode sends prompts to the Ollama service configured in .env. Cloud providers are not enabled in this starter.
