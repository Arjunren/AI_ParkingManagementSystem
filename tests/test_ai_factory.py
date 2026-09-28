from app.extensions import db
from app.models import AIRecommendation, FactoryRun
from app.services.ai.schemas import (
    Finding,
    OperationsAnalysis,
    Priority,
    PriorityIssue,
    Recommendation,
    RecommendationBatch,
    TrafficStatus,
)


class FakeProvider:
    def generate(self, *, instructions, payload, schema):
        if schema is OperationsAnalysis:
            return OperationsAnalysis(
                traffic_status=TrafficStatus.normal,
                congested_zones=[],
                facility_concerns=[],
                maintenance_patterns=[],
                incident_patterns=[],
                feedback_patterns=[],
                reservation_patterns=[],
                priority_issues=[
                    PriorityIssue(title="Review entrance flow", priority=Priority.medium, reason="Entry totals require routine review.")
                ],
                data_gaps=[],
                summary="Operations are within the supplied normal range.",
            )
        return RecommendationBatch(
            needs_additional_analysis=False,
            recommendations=[
                Recommendation(
                    title="Review entrance workflow",
                    category="Visitor Management",
                    priority=Priority.medium,
                    priority_reason="Current visitor totals merit routine review.",
                    reason="The supplied aggregate includes today's entry total.",
                    recommended_action="Review staffing before the next operating period.",
                    related_zone="Main Entrance",
                )
            ],
            summary="One evidence-based recommendation generated.",
        )


class FailingRecommendationProvider(FakeProvider):
    def generate(self, *, instructions, payload, schema):
        if schema is RecommendationBatch:
            raise RuntimeError("simulated provider failure")
        return super().generate(instructions=instructions, payload=payload, schema=schema)


class FeedbackLoopProvider(FakeProvider):
    def __init__(self):
        self.recommendation_calls = 0

    def generate(self, *, instructions, payload, schema):
        if schema is RecommendationBatch:
            self.recommendation_calls += 1
            if self.recommendation_calls == 1:
                return RecommendationBatch(
                    needs_additional_analysis=True,
                    additional_analysis_request="Check whether any supplied zone is above 80 percent capacity.",
                    recommendations=[],
                    summary="A focused capacity check is required.",
                )
        return super().generate(instructions=instructions, payload=payload, schema=schema)


def test_agent_schema_rejects_invalid_priority():
    try:
        Recommendation(
            title="Test recommendation",
            category="Safety",
            priority="Unsupported",
            priority_reason="Test reason",
            reason="Test evidence",
            recommended_action="Test action",
        )
    except Exception as exc:
        assert "priority" in str(exc)
    else:
        raise AssertionError("Invalid priority was accepted")


def test_factory_orchestration_and_approval(app, admin_client):
    app.config["AI_PROVIDER"] = FakeProvider()
    response = admin_client.post("/api/factory/start", json={})
    assert response.status_code == 202
    run = response.get_json()["run"]
    assert run["status"] == "Completed"
    assert run["recommendation_count"] == 1
    recommendation = admin_client.get("/api/recommendations").get_json()["items"][0]
    approved = admin_client.post(
        f"/api/recommendations/{recommendation['id']}/approve",
        json={"admin_note": "Reviewed by administrator."},
    )
    assert approved.get_json()["item"]["status"] == "Approved"
    implemented = admin_client.post(
        f"/api/recommendations/{recommendation['id']}/implement",
        json={"admin_note": "Completed after field verification."},
    )
    assert implemented.get_json()["item"]["status"] == "Implemented"


def test_agent_two_failure_is_partial_and_retryable(app, admin_client):
    app.config["AI_PROVIDER"] = FailingRecommendationProvider()
    response = admin_client.post("/api/factory/start", json={})
    run = response.get_json()["run"]
    assert run["status"] == "Partial Failure"
    app.config["AI_PROVIDER"] = FakeProvider()
    retry = admin_client.post(f"/api/factory/{run['id']}/retry-agent-2", json={})
    assert retry.status_code == 202
    assert retry.get_json()["run"]["status"] == "Completed"


def test_feedback_loop_runs_at_most_one_additional_iteration(app, admin_client):
    provider = FeedbackLoopProvider()
    app.config["AI_PROVIDER"] = provider
    response = admin_client.post("/api/factory/start", json={})
    run = response.get_json()["run"]
    assert run["status"] == "Completed"
    assert run["iteration_count"] == 2
    assert len(run["agents"]) == 4
    assert provider.recommendation_calls == 2
