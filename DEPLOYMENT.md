# Deployment

## Local development

Use Python 3.11 or newer, create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, generate a strong `SECRET_KEY`, initialize an administrator, and run Flask. SQLite data is written below `instance/` and is intentionally ignored.

## Production checklist

1. Use PostgreSQL and set `DATABASE_URL` to a TLS-enabled connection string.
2. Set `FLASK_ENV=production`, a random `SECRET_KEY`, `OPENAI_API_KEY`, and the approved `OPENAI_MODEL` through the platform secret manager.
3. Run database migrations before switching traffic.
4. Serve with Gunicorn behind an HTTPS reverse proxy, for example `gunicorn 'app:create_app()'`.
5. Set `RATELIMIT_STORAGE_URI` to a private Redis endpoint when running multiple workers; do not use the in-memory backend across replicas.
6. Restrict outbound traffic, centralize application logs, back up the database, and monitor factory failures and repeated authentication failures.
7. Run `pytest`, dependency auditing, and a manual role/CSRF review for every release.

The in-process background thread is suitable for this medium student project. A production-scale deployment should move factory jobs to a durable queue while retaining the same database run state and two-agent contracts.

## Container and AWS reference deployment

`Dockerfile` runs the web process as an unprivileged user on port `8000`; `GET /health` is the load-balancer readiness check. For a local container smoke test, copy `.env.example` to `.env`, set a development `SECRET_KEY`, and run:

```powershell
docker compose up --build
```

The checked-in AWS foundation is in [`terraform/aws`](terraform/aws). It provisions a multi-AZ VPC, HTTPS application load balancer, private ECS Fargate web service, CloudWatch logging, and private PostgreSQL database. It deliberately accepts **secret ARNs**, never secret values. Create the database URL, Flask secret, and OpenAI key in AWS Secrets Manager before planning. See [`terraform/aws/README.md`](terraform/aws/README.md) for the deployment sequence.
