# Security

## Controls

- Passwords are hashed with Werkzeug and sessions are managed by Flask-Login.
- CSRF validation covers forms and same-origin Fetch mutations.
- Administrator-only routes enforce role checks on the server; hidden UI is never treated as authorization.
- SQLAlchemy parameter binding prevents SQL injection, Jinja autoescaping mitigates XSS, input is allow-list validated, and a restrictive Content Security Policy is applied.
- Login and write-heavy endpoints are rate limited. Request bodies are capped at 2 MB.
- `.env` is ignored. The OpenAI key is used only in the server-side provider adapter.
- AI requests contain aggregate operational facts, have a timeout and output limit, and are validated against Pydantic schemas.
- Error handlers return safe messages while operational logs avoid secrets and hidden model reasoning.
- Dependencies are version-bounded and should be reviewed with `pip-audit` before production deployment.

## OWASP considerations

Access control is enforced through authentication and role decorators; passwords and session cookies use secure defaults; ORM queries and validation address injection; human approval and bounded agent loops support secure design; environment-based configuration avoids embedded secrets; dependency ranges and deployment reviews cover component risk; login throttling addresses authentication attacks; source control and locked deployment practices protect integrity; activity and agent logs support monitoring; and the application does not accept user-controlled outbound URLs, reducing SSRF exposure.

## Reporting a vulnerability

Do not open a public issue containing secrets or exploit details. Contact the repository owner privately with reproduction steps and affected versions.

