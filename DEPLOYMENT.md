# Deployment

## Local development

Use Python 3.11 or newer, create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, generate a strong `SECRET_KEY`, initialize an administrator, and run Flask. SQLite data is written below `instance/` and is intentionally ignored.

## Production checklist

1. Use PostgreSQL and set `DATABASE_URL` to a TLS-enabled connection string.
2. Set `FLASK_ENV=production`, a random `SECRET_KEY`, `OPENAI_API_KEY`, and the approved `OPENAI_MODEL` through the platform secret manager.
3. Run database migrations before switching traffic.
4. Serve with Gunicorn behind an HTTPS reverse proxy, for example `gunicorn 'app:create_app()'`.
5. Replace the in-memory rate-limit backend with Redis when running multiple workers.
6. Restrict outbound traffic, centralize application logs, back up the database, and monitor factory failures and repeated authentication failures.
7. Run `pytest`, dependency auditing, and a manual role/CSRF review for every release.

The in-process background thread is suitable for this medium student project. A production-scale deployment should move factory jobs to a durable queue while retaining the same database run state and two-agent contracts.

