# ParkSmart AI implementation plan

## Delivery phases

1. Establish the Flask application factory, configuration, database extension, security middleware, shared layout, and documentation skeleton.
2. Add the relational schema, administrator/staff authentication, role checks, activity logging, and administrative user tooling.
3. Implement the operational modules and their JSON APIs: visitors, tickets/prices, zones, facilities, reservations, maintenance, incidents, feedback, and staff.
4. Add the dashboard, operational analytics, charts, reports, and CSV/JSON/print exports.
5. Implement exactly two AI agents with independent prompts, Pydantic contracts, execution logs, a single bounded feedback iteration, and partial-failure recovery.
6. Add the factory monitor and recommendation review workflow, then harden error handling and security.
7. Run automated tests, verify the application manually, finish documentation, commit, create the GitHub repository, push, and verify the remote.

## Architecture decisions

- Flask blueprints isolate authentication, operational resources, reports, and AI Factory endpoints.
- SQLAlchemy keeps persistence portable between SQLite and PostgreSQL. Relationships and indexes enforce the important data boundaries.
- The OpenAI provider adapter is the only layer that imports the OpenAI SDK. Business services depend on a small structured-generation interface.
- Pydantic schemas validate both agent outputs before data moves between agents or becomes a recommendation.
- Factory runs execute in a background thread in normal development and synchronously in tests. The database is the source of truth for polling.
- Human approval is mandatory. AI output never changes facility, staffing, reservation, or maintenance records.

## Roles

| Capability | Administrator | Park Staff |
| --- | --- | --- |
| Dashboard and operational records | Full | Full |
| Ticket pricing and zones | Manage | View |
| Staff/users | Manage | No access |
| Reports | Full | No access |
| Start/retry AI Factory | Yes | No |
| Approve/reject/implement recommendations | Yes | No |

## Security baseline

- Werkzeug password hashing, Flask-Login sessions, CSRF protection, role decorators, parameterized ORM queries, strict validation, output escaping, upload-size limits, login/API rate limits, secure cookie settings, defensive response headers, and generic production errors.
- OpenAI keys remain server-side, calls have timeouts, logs store summaries rather than prompts or chain-of-thought, and only aggregate operational data is sent to the model.
- Factory execution is manual, duplicate running jobs are rejected, output tokens are capped, and the feedback loop permits one additional Agent 1 pass only.

## Primary dependencies

Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Limiter, Pydantic, the OpenAI Python SDK, python-dotenv, psycopg, pytest, and pytest-cov. Tailwind CSS and Chart.js are loaded in the browser for the student-oriented local build.

