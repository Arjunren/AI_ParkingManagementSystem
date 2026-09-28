# ParkSmart AI — Final Project Blueprint

## 1. Executive summary

ParkSmart AI is an **AI Platform** for operating a public park and an **AI Factory** that converts verified operating data into human-approved recommendations. It is intentionally not a chatbot: the system records park operations, aggregates the relevant facts, routes them through exactly two specialized AI agents, validates every structured response, and requires an administrator to make the final decision.

### Final-project objective

Demonstrate a secure, maintainable, medium-complexity agentic system in which:

1. Staff operate a real park-management workflow.
2. The platform produces privacy-minimized operational snapshots.
3. Agent 1 analyzes facts and patterns.
4. Agent 2 produces evidence-based actions.
5. A human approves, rejects, or implements each recommendation.
6. Every factory run, agent state, error, and review decision remains auditable.

## 2. Business scope and users

| User | Primary outcome | Permissions |
| --- | --- | --- |
| Administrator | Control operations and decide on AI proposals | Full access, users, pricing, reports, AI Factory, recommendation review |
| Park Staff | Record and maintain daily operations | Visitors, tickets, facilities, reservations, maintenance, incidents, feedback |
| Visitor | Share privacy-respecting feedback | Anonymous feedback submission only |

### Platform modules

- Authentication and role-based access control
- Dashboard and operational analytics
- Visitors and entrance tickets
- Park zones and facilities
- Facility reservations
- Maintenance and incident reporting
- Visitor feedback and staff management
- Reports and exports
- AI Factory monitor, run history, agent logs, and recommendation dashboard

## 3. Target architecture

```text
Users
  |
  v
HTTPS / WAF / Load Balancer
  |
  v
Flask Web Application ────> PostgreSQL (system of record)
  |                              |
  |                              +--> backups / encryption / read replicas later
  |
  +--> Redis (rate limits, job coordination, cache)
  |
  +--> AI Factory Worker Queue
           |
           +--> Agent 1: Park Operations Analyst
           |       |
           |       +--> validated OperationsAnalysis
           |
           +--> Agent 2: Park Recommendation Agent
                   |
                   +--> validated RecommendationBatch
                           |
                           v
                    Administrator decision

Observability: structured logs, metrics, traces, audit events, alarms
Secrets: managed secret store; never browser JavaScript or source control
```

### Logical layers

| Layer | Responsibility | Technology choice |
| --- | --- | --- |
| Presentation | Responsive forms, dashboards, polling, approval UX | HTML5, Jinja2, Tailwind CSS, vanilla JavaScript |
| HTTP/API | Authentication, validation, authorization, response codes | Flask blueprints |
| Domain services | Reservation collision checks, analytics snapshots, factory orchestration | Python services |
| AI integration | Structured generation and provider error normalization | OpenAI Responses API adapter + Pydantic |
| Persistence | Transactions, constraints, relationships, indexes | SQLAlchemy; SQLite locally, PostgreSQL in production |
| Asynchronous work | Durable factory jobs and retries in production | Redis-backed queue/worker |
| Infrastructure | Network, container compute, managed database, secrets, logs | Terraform + cloud provider modules |

## 4. Agentic AI design

### Constraint: exactly two primary agents

The system has **two and only two primary AI agents**. Supporting components such as the orchestrator, database queries, validator, and queue worker are deterministic software services, not additional agents.

| Agent | Goal | Inputs | Output | Never does |
| --- | --- | --- | --- | --- |
| Park Operations Analyst | Identify operational patterns and evidence | Aggregated park snapshot; optional focused follow-up | `OperationsAnalysis` | Recommend actions, mutate data, request personal information |
| Park Recommendation Agent | Propose feasible, evidence-based actions | Snapshot + validated Agent 1 analysis | `RecommendationBatch` | Invent evidence, apply a change, bypass administrator approval |

### Agent 1 contract — Park Operations Analyst

**System prompt principles**

- Analyze only supplied aggregate facts.
- Cite evidence for each finding.
- Record data gaps instead of guessing.
- Separate observations from recommendations.
- Never send, request, or infer personal information.

**Privacy-minimized input example**

```json
{
  "date": "2026-09-28",
  "visitors": {"count": 1450, "currently_inside": 450, "entry_by_hour": []},
  "zones": [{"name": "Playground", "occupancy_percent": 92.0, "status": "Open"}],
  "facilities": [{"name": "Comfort Room 2", "status": "Under Maintenance"}],
  "maintenance_reports": [],
  "incidents": [],
  "feedback": {"count": 14, "categories": []},
  "tickets": {"sold": 1450, "revenue": "65000.00"}
}
```

**Validated output**

```text
OperationsAnalysis
├── traffic_status: low | normal | high | critical
├── peak_periods[]
├── congested_zones[]
├── facility_concerns[]
├── maintenance_patterns[]
├── incident_patterns[]
├── feedback_patterns[]
├── reservation_patterns[]
├── priority_issues[]
├── data_gaps[]
└── summary
```

### Agent 2 contract — Park Recommendation Agent

**System prompt principles**

- Consume Agent 1's validated analysis and the original snapshot.
- Create only concrete, feasible actions grounded in supplied evidence.
- Give each priority a short evidence-based reason.
- Describe proposals as proposals; a human must decide.
- Request a focused extra analysis only if a missing fact could materially change the recommendation.

**Validated output**

```text
RecommendationBatch
├── needs_additional_analysis: boolean
├── additional_analysis_request: string
├── recommendations[]
│   ├── title
│   ├── category
│   ├── priority: Low | Medium | High | Critical
│   ├── priority_reason
│   ├── reason
│   ├── recommended_action
│   ├── related_zone
│   └── related_facility
└── summary
```

## 5. AI Factory workflow

```text
Administrator starts a manual run
            |
            v
Aggregate operational snapshot (no unnecessary PII)
            |
            v
Run Agent 1 and validate OperationsAnalysis
            |
            +--> failure: mark run Failed; save safe operational error
            |
            v
Run Agent 2 and validate RecommendationBatch
            |
            +--> needs more evidence?
            |        |
            |        +--> Yes: one focused Agent 1 pass, then final Agent 2 pass
            |        |           (no further loops permitted)
            |        |
            |        +--> No: persist recommendations
            |
            +--> Agent 2 failure: mark Partial Failure; retain Agent 1 output
            |                         and allow Agent 2 retry only
            v
Recommendations are Pending
            |
            v
Administrator approves, rejects, or marks implemented
```

### Run states and recovery

| Condition | Factory state | Recovery |
| --- | --- | --- |
| Agent 1 succeeds, Agent 2 succeeds | Completed | Normal administrator review |
| Agent 1 fails | Failed | Correct configuration/data issue; start a new run |
| Agent 1 succeeds, Agent 2 fails | Partial Failure | Retry Agent 2 using stored snapshot and analysis |
| Invalid structured output | Failed or Partial Failure | Save safe error; do not persist invalid recommendations |
| Run already active | Rejected at API boundary | Return `409 Conflict` and avoid duplicate cost |

## 6. API blueprint

### Authentication and platform

| Method | Endpoint | Role | Purpose |
| --- | --- | --- | --- |
| `POST` | `/login` | Public | Begin authenticated session |
| `POST` | `/logout` | Authenticated | End session |
| `GET` | `/api/dashboard` | Authenticated | Dashboard metrics and chart data |
| `GET` | `/api/users` | Administrator | List application accounts |
| `POST` | `/api/users` | Administrator | Create staff/administrator account |

### Park operations

| Resource | Collection endpoint | Item endpoint | Notes |
| --- | --- | --- | --- |
| Visitors | `GET, POST /api/visitors` | `PUT, DELETE /api/visitors/{id}` | Exit event: `POST /api/visitors/{id}/exit` |
| Tickets | `GET, POST /api/tickets` | `PUT /api/tickets/{id}` | Prices: `GET, POST /api/ticket-prices` |
| Zones | `GET, POST /api/zones` | `PUT /api/zones/{id}` | Zone writes are administrator-only |
| Facilities | `GET, POST /api/facilities` | `PUT, DELETE /api/facilities/{id}` | Inspection dates and operational status |
| Reservations | `GET, POST /api/reservations` | `PUT, DELETE /api/reservations/{id}` | Validates time overlap and capacity |
| Maintenance | `GET, POST /api/maintenance` | `PUT /api/maintenance/{id}` | Preserves history and completion time |
| Incidents | `GET, POST /api/incidents` | `PUT /api/incidents/{id}` | Severity, response, and status |
| Feedback | `GET, POST /api/feedback` | `PUT /api/feedback/{id}` | Anonymous public form at `/feedback/submit` |

### AI Factory and reporting

| Method | Endpoint | Role | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/factory/start` | Administrator | Start manual analysis |
| `GET` | `/api/factory/{id}/status` | Administrator | Poll status and individual agent states |
| `GET` | `/api/factory/runs` | Administrator | Run history |
| `POST` | `/api/factory/{id}/retry-agent-2` | Administrator | Recover Agent 2 only after partial failure |
| `GET` | `/api/recommendations` | Administrator | Filter recommendations by status/priority/category |
| `POST` | `/api/recommendations/{id}/approve` | Administrator | Approve with optional note |
| `POST` | `/api/recommendations/{id}/reject` | Administrator | Reject with optional note |
| `POST` | `/api/recommendations/{id}/implement` | Administrator | Mark approved work implemented |
| `GET` | `/api/reports/{type}` | Administrator | Date-filtered report data |
| `GET` | `/reports/{type}/export.{csv|json|html}` | Administrator | Download or print report |

### API rules

- Require authentication for every protected route and JSON `401` responses for unauthenticated API callers.
- Require server-side role checks; hiding a button is never authorization.
- Require CSRF tokens for same-origin mutations.
- Validate request bodies with allow-lists and return `400`, `403`, `404`, `409`, `429`, or `500` appropriately.
- Never return secrets, full stack traces, hidden prompts, chain-of-thought, or unnecessary contact information.

## 7. Database blueprint

```text
users ──< activity_logs
  |  └──< visitors ──< tickets
  |  └──< maintenance_requests
  |  └──< incident_reports
  |  └──< factory_runs ──< agent_runs
  |                      └──< ai_recommendations
  |
staff >── park_zones ──< facilities ──< reservations
              |                └──< maintenance_requests
              └──< incident_reports
              └──< visitor_feedback

ticket_prices are category-level configuration records.
```

| Table | Purpose | Key integrity rules |
| --- | --- | --- |
| `users` | Login identity and role | Unique username; hashed password only |
| `staff` | Employee profile and zone assignment | Unique employee ID; optional zone FK |
| `visitors` | Minimal entry/exit record | No unnecessary PII; creation audit |
| `tickets`, `ticket_prices` | Entrance transaction state and category fees | Unique ticket/category; no payment-card data |
| `park_zones`, `facilities` | Physical park inventory | Capacity/status constraints; zone FKs |
| `reservations` | Time-bound facility usage | Index on facility/date/status; service-level overlap check |
| `maintenance_requests`, `incident_reports` | Risk and operating history | Priority/severity/status allow-lists |
| `visitor_feedback` | Anonymous service-quality signal | Optional facility/zone link |
| `factory_runs`, `agent_runs` | AI execution state | Run and agent/iteration uniqueness |
| `ai_recommendations` | Human-controlled proposals | Pending/Approved/Rejected/Implemented transition rules |
| `activity_logs` | Audit trail | Actor, action, entity, timestamp |

### Production database practices

- Use PostgreSQL with TLS, encrypted storage, automatic backups, point-in-time recovery, and a private subnet.
- Use reviewed Alembic migrations; do not use auto-create tables in production.
- Add database constraints for enums/checks as the schema matures.
- Preserve operational history; implement retention/anonymization policies for visitor-related data.
- Separate database credentials by environment and rotate them through the secret manager.

## 8. Terraform infrastructure blueprint

### Reference production topology (AWS example)

```text
Internet
  |
  v
Route 53 / ACM / WAF
  |
  v
Application Load Balancer (public subnets, HTTPS)
  |
  v
ECS Fargate service (private subnets)
  |             |
  |             +--> worker service / queue consumer
  |
  +--> RDS PostgreSQL (private isolated subnets)
  +--> ElastiCache Redis (private subnets)
  +--> Secrets Manager
  +--> CloudWatch logs, alarms, and dashboard
```

### Recommended Terraform repository layout

```text
terraform/
├── bootstrap/                 # One-time remote state bucket and lock table
├── modules/
│   ├── network/               # VPC, subnets, NAT, routes, VPC endpoints
│   ├── security/              # Security groups, WAF, IAM roles/policies
│   ├── database/              # RDS PostgreSQL, backups, parameter group
│   ├── cache/                 # Redis for rate limits and job coordination
│   ├── compute/               # ECS cluster, web and worker task definitions
│   ├── edge/                  # ALB, TLS listener, Route 53 records
│   ├── secrets/               # Secret references and least-privilege grants
│   └── observability/         # Log groups, alarms, dashboard, audit trail
└── environments/
    ├── dev/
    ├── staging/
    └── production/
```

### Terraform module responsibilities

| Module | Creates | Critical controls |
| --- | --- | --- |
| `network` | Multi-AZ VPC, public/private/isolated subnets, NAT and endpoints | Database has no public route; least-cost dev topology may use one AZ |
| `security` | Security groups, task roles, execution roles, WAF | ALB accepts 443; app accepts traffic only from ALB; DB accepts 5432 only from app |
| `database` | PostgreSQL, subnet group, KMS encryption, backups | Private access, TLS, backup retention, deletion protection in production |
| `cache` | Redis replication group or serverless cache | Private access; encryption in transit/at rest |
| `compute` | Fargate web service and worker service | Immutable image tag, non-root container, health checks, autoscaling |
| `edge` | ALB, ACM certificate, HTTPS listener, DNS | TLS-only, access logs, WAF association |
| `secrets` | References to application secrets | Inject by ARN at runtime; never expose values in Terraform outputs/state |
| `observability` | Logs, metrics, alarms, dashboards | Retention, alerts for 5xx, queue depth, failed runs, DB capacity |

### Terraform inputs and secret policy

```hcl
# Example: pass secret ARNs, never literal secret values.
variable "openai_api_key_secret_arn" { type = string }
variable "database_url_secret_arn" { type = string }
variable "flask_secret_key_secret_arn" { type = string }
variable "container_image" { type = string }
variable "environment" { type = string }

# ECS container definition injects secrets at runtime.
secrets = [
  { name = "OPENAI_API_KEY", valueFrom = var.openai_api_key_secret_arn },
  { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
  { name = "SECRET_KEY", valueFrom = var.flask_secret_key_secret_arn }
]
```

### Infrastructure delivery sequence

1. Bootstrap encrypted remote state and state locking in a dedicated account/project.
2. Plan in CI with environment-specific variables; do not apply from a developer laptop in production.
3. Provision network, identity, logs, database, cache, and secrets before compute.
4. Build and scan a container image; push an immutable digest to the image registry.
5. Run database migration as a one-off task using the same secure network and secret references.
6. Deploy the web service, then the worker service; use health checks and rolling deployment.
7. Enable alarms and verify backup/restore plus the Agent 2 partial-failure recovery path.

## 9. Security blueprint

### Application security

- Password hashing, short-lived server-side sessions, `HttpOnly`, `Secure`, and `SameSite` cookie settings.
- CSRF protection for forms and Fetch mutations.
- RBAC at every route and API boundary.
- Pydantic/request allow-list validation, ORM parameter binding, Jinja autoescaping, CSP, secure headers, and request-size limits.
- Login/write rate limiting backed by Redis in multi-instance deployments.
- Safe error responses; structured internal logs without credentials, personal data, or hidden reasoning.

### AI and data security

- The browser never receives the OpenAI key.
- Send aggregate operational data only; avoid names, contacts, payment data, and unique visitor identifiers.
- Use timeouts, output-token caps, duplicate-run prevention, and manual trigger controls.
- Validate structured output before Agent 2 consumption or persistence.
- Store operational summaries, not hidden chain-of-thought.
- Require a human approval state before any real-world operational change.

### Cloud and supply-chain security

- Encrypt databases, caches, logs, backups, and Terraform state with customer-managed or provider-managed KMS keys as required.
- Scope IAM roles to exact secret ARNs, log groups, queues, and database/network needs.
- Scan dependencies, container images, and Infrastructure as Code in CI.
- Pin dependencies and container image digests; generate an SBOM for final delivery.
- Use protected main branches, required reviews, CI checks, and environment approvals.

## 10. Implementation phases and acceptance gates

| Phase | Deliverable | Acceptance gate |
| --- | --- | --- |
| 1. Foundation | App factory, configuration, shared UI, documentation | Local app starts; secret files ignored |
| 2. Identity and data | RBAC, schema, migrations, audit logs | Admin/staff permissions tested |
| 3. Core operations | Visitor through feedback modules | CRUD and validation tests pass |
| 4. Analytics and reports | Dashboard, charts, exports | Numbers reconcile with stored data |
| 5. Agent 1 | Snapshot builder, contract, provider adapter | Invalid AI output rejected safely |
| 6. Agent 2 | Recommendation contract and priority evidence | No recommendation changes operations automatically |
| 7. Factory orchestration | Logs, status polling, bounded feedback loop, retry | Agent 2 retry reuses Agent 1 output |
| 8. Hardening | OWASP controls, safe errors, rate limits | Unauthorized and malformed requests tested |
| 9. Production readiness | PostgreSQL, Redis queue, Terraform, CI/CD | Staging deploy, migration, rollback, backup test |
| 10. Final defense | Demo script, screenshots, report, architecture presentation | End-to-end scenario works from login to approval |

## 11. Final demonstration script

1. Log in as an administrator.
2. Show visitors, zones, facilities, reservations, maintenance reports, incidents, and feedback records.
3. Explain that the dashboard numbers come from stored operational data.
4. Start an AI Factory run.
5. Show Agent 1's independent analysis status and safe aggregate input summary.
6. Show Agent 2's recommendations and the stored run/agent logs.
7. Open a high-priority recommendation and explain its evidence and priority reason.
8. Approve it, add an administrator note, and mark it implemented only after a human decision.
9. Show report export and audit activity.
10. Explain the one-iteration limit, Agent 2-only retry path, privacy controls, and Terraform production architecture.

## 12. Success criteria checklist

- [ ] Exactly two primary AI agents, each with a distinct prompt, contract, service, and state.
- [ ] Real operational system data is aggregated and privacy-minimized before AI use.
- [ ] Structured output is validated before every agent handoff and persistence action.
- [ ] Agent 2 cannot create unsupported claims or apply changes automatically.
- [ ] Human approval is mandatory and auditable.
- [ ] Factory runs support logs, history, bounded iteration, partial failure, and Agent 2 retry.
- [ ] API, database, RBAC, report, and reservation controls are tested.
- [ ] Production plan includes PostgreSQL, Redis-backed work, TLS, secrets, observability, and Terraform modules.
- [ ] Documentation clearly distinguishes the current local student build from the production target architecture.

