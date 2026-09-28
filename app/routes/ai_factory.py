from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from app.extensions import db, limiter
from app.models import AIRecommendation, AgentRun, FactoryRun
from app.routes.common import json_data, validation_error
from app.services.ai.factory import AIFactory, FactoryBusyError
from app.utils.activity import record_activity
from app.utils.auth import admin_required
from app.utils.validation import ValidationError, optional_text


bp = Blueprint("ai_factory", __name__)


def serialize_agent(item: AgentRun) -> dict:
    return {
        "id": item.id,
        "name": item.agent_name,
        "status": item.status,
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "ended_at": item.ended_at.isoformat() if item.ended_at else None,
        "input_summary": item.input_summary or {},
        "output_summary": item.output_summary or {},
        "error": item.error,
        "iteration": item.iteration,
    }


def serialize_run(item: FactoryRun, *, include_agents=True) -> dict:
    completed_agents = sum(1 for agent in item.agent_runs if agent.status == "Completed")
    total_agents = max(len(item.agent_runs), 2)
    progress = 100 if item.status in {"Completed", "Failed", "Partial Failure"} else int((completed_agents / total_agents) * 100)
    data = {
        "id": item.id,
        "run_date": item.run_date.isoformat(),
        "started_at": item.started_at.isoformat(),
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "status": item.status,
        "triggered_by": item.triggered_by.username,
        "recommendation_count": item.recommendation_count,
        "priority_issue_count": item.priority_issue_count,
        "iteration_count": item.iteration_count,
        "progress": progress,
    }
    if include_agents:
        data["agents"] = [
            serialize_agent(agent)
            for agent in sorted(item.agent_runs, key=lambda value: (value.iteration, value.id))
        ]
    return data


def serialize_recommendation(item: AIRecommendation) -> dict:
    return {
        "id": item.id,
        "factory_run_id": item.factory_run_id,
        "title": item.title,
        "category": item.category,
        "priority": item.priority,
        "priority_reason": item.priority_reason,
        "reason": item.reason,
        "recommended_action": item.recommended_action,
        "related_zone": item.related_zone,
        "related_facility": item.related_facility,
        "generated_at": item.generated_at.isoformat(),
        "status": item.status,
        "admin_note": item.admin_note,
        "reviewed_by": item.reviewed_by.username if item.reviewed_by else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
    }


@bp.get("/ai-factory")
@admin_required
def factory_page():
    latest = FactoryRun.query.order_by(FactoryRun.started_at.desc()).first()
    return render_template("ai_factory.html", latest_run_id=latest.id if latest else "")


@bp.get("/recommendations")
@admin_required
def recommendations_page():
    return render_template("recommendations.html")


@bp.post("/api/factory/start")
@admin_required
@limiter.limit("10 per hour")
def start_factory():
    try:
        run = AIFactory().start(current_user.id)
        record_activity("Started AI Factory", "FactoryRun", run.id, "Manual run")
        db.session.commit()
        refreshed = db.session.get(FactoryRun, run.id)
        return jsonify({"run": serialize_run(refreshed)}), 202
    except FactoryBusyError as exc:
        return jsonify({"error": str(exc)}), 409


@bp.post("/api/factory/<run_id>/retry-agent-2")
@admin_required
@limiter.limit("10 per hour")
def retry_agent_two(run_id: str):
    try:
        run = AIFactory().retry_agent_two(run_id)
        record_activity("Retried recommendation agent", "FactoryRun", run.id, "Agent 2 retry")
        db.session.commit()
        return jsonify({"run": serialize_run(db.session.get(FactoryRun, run.id))}), 202
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@bp.get("/api/factory/<run_id>/status")
@admin_required
def factory_status(run_id: str):
    run = db.get_or_404(FactoryRun, run_id)
    return jsonify({"run": serialize_run(run)})


@bp.get("/api/factory/runs")
@admin_required
def factory_runs():
    items = FactoryRun.query.order_by(FactoryRun.started_at.desc()).limit(50).all()
    return jsonify({"items": [serialize_run(item, include_agents=False) for item in items]})


@bp.get("/api/recommendations")
@admin_required
def recommendations():
    query = AIRecommendation.query
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    category = request.args.get("category", "").strip()
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(AIRecommendation.generated_at.desc()).limit(500).all()
    return jsonify({"items": [serialize_recommendation(item) for item in items]})


@bp.post("/api/recommendations/<int:item_id>/<action>")
@admin_required
def recommendation_action(item_id: int, action: str):
    item = db.get_or_404(AIRecommendation, item_id)
    transitions = {
        "approve": ({"Pending"}, "Approved"),
        "reject": ({"Pending", "Approved"}, "Rejected"),
        "implement": ({"Approved"}, "Implemented"),
    }
    if action not in transitions:
        return jsonify({"error": "Unknown recommendation action."}), 404
    allowed, target = transitions[action]
    if item.status not in allowed:
        return jsonify({"error": f"A {item.status.lower()} recommendation cannot be marked {target.lower()}."}), 409
    try:
        data = request.get_json(silent=True) or {}
        item.admin_note = optional_text(data, "admin_note", max_length=2000)
        item.status = target
        item.reviewed_by_id = current_user.id
        item.reviewed_at = datetime.now(timezone.utc)
        record_activity(f"{target} AI recommendation", "AIRecommendation", item.id, item.title)
        db.session.commit()
        return jsonify({"item": serialize_recommendation(item)})
    except ValidationError as exc:
        return validation_error(exc)

