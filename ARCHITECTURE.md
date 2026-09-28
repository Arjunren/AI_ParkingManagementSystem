# ParkSmart AI architecture

```text
ParkSmart AI Platform
        |
        v
Operational services + aggregated snapshot
        |
        v
AI Factory Orchestrator
        |
        +--> Park Operations Analyst (Agent 1)
        |        |
        |        v
        |   OperationsAnalysis schema
        |        |
        |   optional focused re-analysis (maximum once)
        |        ^
        |        |
        +--> Park Recommendation Agent (Agent 2)
                 |
                 v
          RecommendationBatch schema
                 |
                 v
          Administrator review
```

## Application layers

- **Presentation:** Jinja templates, Tailwind CSS, and vanilla JavaScript. Fetch requests include the session CSRF token.
- **Routes:** Blueprints expose protected HTML pages and JSON APIs. Authorization is checked at the route boundary.
- **Domain and analytics services:** Validate commands, aggregate only necessary operational facts, prevent reservation overlap, and create activity records.
- **Persistence:** SQLAlchemy models use foreign keys, indexes, timestamps, and database-agnostic column types. SQLite is the default; a PostgreSQL URL can be supplied without changing business code.
- **AI provider:** A small OpenAI adapter calls the Responses API with Pydantic structured outputs. Agents do not know about HTTP routes or database sessions.

## Database schema

Core tables are `users`, `staff`, `visitors`, `tickets`, `ticket_prices`, `park_zones`, `facilities`, `reservations`, `maintenance_requests`, `incident_reports`, `visitor_feedback`, `factory_runs`, `agent_runs`, `ai_recommendations`, and `activity_logs`.

Important relationships include zones to facilities/staff, visitors to tickets, facilities to reservations and maintenance, users to authored operational records, factory runs to agent runs/recommendations, and reviewers to recommendation decisions. Reservation lookups are indexed by facility/date/status so overlap checks stay efficient.

## Agent contracts

### Agent 1 — Park Operations Analyst

Input is a privacy-minimized daily snapshot containing counts, time buckets, capacity/usage summaries, maintenance issue summaries, incident summaries, feedback category summaries, and ticket totals. No visitor names, contacts, staff contacts, or payment details are included.

Output is the `OperationsAnalysis` schema: traffic status, evidence-based peak periods, congested zones, facility concerns, maintenance/incident/feedback patterns, priority issues, data gaps, and a concise summary. A focused follow-up request may be supplied for one extra analysis pass.

### Agent 2 — Park Recommendation Agent

Input contains the same aggregated snapshot plus the validated Agent 1 analysis. Output is the `RecommendationBatch` schema: whether more analysis is required, an optional focused request, and zero or more actionable recommendations with category, priority, priority reason, evidence-based reason, action, and optional related zone/facility.

## Why this is agentic AI

The agents have different goals, prompts, inputs, schemas, services, and execution states. The orchestrator passes validated work from Analyst to Recommender, lets the Recommender request one bounded focused re-analysis, persists each independent run, and recovers from an Agent 2 failure without rerunning Agent 1. This is a controlled multi-step decision workflow rather than a chatbot or duplicated prompt.

## Human control and recovery

Recommendations begin as `Pending` and can only be approved, rejected, or marked implemented by an administrator. They never directly mutate operational data. A successful Analyst run plus a failed Recommender run produces `Partial Failure`; retry reuses the stored snapshot and analysis. Agent logs contain input/output summaries and errors only—never hidden reasoning.

