from datetime import date, datetime
from uuid import uuid4

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import IncidentReport, ParkZone
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.validation import ValidationError, iso_date, iso_time, one_of, optional_text, require_text


bp = Blueprint("incidents", __name__)
TYPES = {"Injury", "Lost Item", "Property Damage", "Safety Concern", "Security Issue", "Overcrowding", "Environmental Issue"}
SEVERITIES = {"Low", "Medium", "High", "Critical"}
STATUSES = {"Open", "Under Review", "Resolved", "Closed"}


def serialize(item: IncidentReport) -> dict:
    return {
        "id": item.id,
        "incident_number": item.incident_number,
        "incident_type": item.incident_type,
        "zone_id": item.zone_id,
        "zone": item.zone.name,
        "incident_date": item.incident_date.isoformat(),
        "incident_time": item.incident_time.strftime("%H:%M"),
        "description": item.description,
        "reported_by": item.reported_by.username,
        "severity": item.severity,
        "status": item.status,
        "action_taken": item.action_taken,
    }


@bp.get("/incidents")
@login_required
def page():
    zones = ParkZone.query.order_by(ParkZone.name).all()
    config = page_config(
        title="Incident Reporting",
        subtitle="Record safety, security, environmental, and crowding events.",
        endpoint="/api/incidents",
        columns=[
            {"key": "incident_number", "label": "Incident"},
            {"key": "incident_type", "label": "Type"},
            {"key": "zone", "label": "Zone"},
            {"key": "incident_date", "label": "Date"},
            {"key": "severity", "label": "Severity", "badge": True},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "incident_type", "label": "Incident type", "type": "select", "options": sorted(TYPES), "required": True},
            {"name": "zone_id", "label": "Park zone", "type": "select", "options": [{"value": z.id, "label": z.name} for z in zones], "required": True},
            {"name": "incident_date", "label": "Date", "type": "date", "value": date.today().isoformat(), "required": True},
            {"name": "incident_time", "label": "Time", "type": "time", "value": datetime.now().strftime("%H:%M"), "required": True},
            {"name": "description", "label": "Description", "type": "textarea", "required": True},
            {"name": "severity", "label": "Severity", "type": "select", "options": sorted(SEVERITIES), "value": "Low", "required": True},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(STATUSES), "value": "Open", "required": True},
            {"name": "action_taken", "label": "Action taken", "type": "textarea"},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/api/incidents")
@login_required
def list_incidents():
    items = IncidentReport.query.order_by(IncidentReport.incident_date.desc(), IncidentReport.incident_time.desc()).limit(500)
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/incidents")
@login_required
def create_incident():
    try:
        item = IncidentReport(
            incident_number=f"INC-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}",
            reported_by_id=current_user.id,
        )
        _apply(item, json_data())
        db.session.add(item)
        db.session.flush()
        record_activity("Reported incident", "IncidentReport", item.id, item.incident_number)
        db.session.commit()
        return jsonify({"item": serialize(item)}), 201
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.put("/api/incidents/<int:item_id>")
@login_required
def update_incident(item_id: int):
    item = db.get_or_404(IncidentReport, item_id)
    try:
        _apply(item, json_data())
        record_activity("Updated incident", "IncidentReport", item.id, item.incident_number)
        db.session.commit()
        return jsonify({"item": serialize(item)})
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


def _apply(item: IncidentReport, data: dict) -> None:
    zone = db.session.get(ParkZone, int(data.get("zone_id", 0)))
    if not zone:
        raise ValidationError("A valid park zone is required.")
    item.zone = zone
    item.incident_type = one_of(data, "incident_type", TYPES)
    item.incident_date = iso_date(data, "incident_date")
    item.incident_time = iso_time(data, "incident_time")
    item.description = require_text(data, "description", max_length=3000)
    item.severity = one_of(data, "severity", SEVERITIES, default="Low")
    item.status = one_of(data, "status", STATUSES, default="Open")
    item.action_taken = optional_text(data, "action_taken", max_length=3000)

