from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Facility, MaintenanceRequest, ParkZone, Staff
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.validation import ValidationError, one_of, optional_text, require_text


bp = Blueprint("maintenance", __name__)
PRIORITIES = {"Low", "Medium", "High", "Critical"}
STATUSES = {"Open", "Assigned", "In Progress", "Completed", "Cancelled"}


def serialize(item: MaintenanceRequest) -> dict:
    return {
        "id": item.id,
        "facility_id": item.facility_id,
        "facility": item.facility.name if item.facility else "—",
        "zone_id": item.zone_id,
        "zone": item.zone.name,
        "issue_title": item.issue_title,
        "description": item.description,
        "priority": item.priority,
        "reported_by": item.reported_by.username,
        "report_date": item.report_date.isoformat(),
        "assigned_staff_id": item.assigned_staff_id,
        "assigned_staff": item.assigned_staff.name if item.assigned_staff else "Unassigned",
        "status": item.status,
        "completion_date": item.completion_date.isoformat() if item.completion_date else None,
    }


@bp.get("/maintenance")
@login_required
def page():
    facilities = Facility.query.order_by(Facility.name).all()
    zones = ParkZone.query.order_by(ParkZone.name).all()
    staff = Staff.query.order_by(Staff.name).all()
    config = page_config(
        title="Maintenance Management",
        subtitle="Report, assign, and preserve the complete maintenance history.",
        endpoint="/api/maintenance",
        columns=[
            {"key": "issue_title", "label": "Issue"},
            {"key": "facility", "label": "Facility"},
            {"key": "zone", "label": "Zone"},
            {"key": "priority", "label": "Priority", "badge": True},
            {"key": "assigned_staff", "label": "Assigned"},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "issue_title", "label": "Issue title", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "textarea", "required": True},
            {"name": "zone_id", "label": "Park zone", "type": "select", "options": [{"value": z.id, "label": z.name} for z in zones], "required": True},
            {"name": "facility_id", "label": "Facility (optional)", "type": "select", "options": [{"value": "", "label": "No specific facility"}] + [{"value": f.id, "label": f.name} for f in facilities]},
            {"name": "priority", "label": "Priority", "type": "select", "options": sorted(PRIORITIES), "value": "Medium", "required": True},
            {"name": "assigned_staff_id", "label": "Assigned staff", "type": "select", "options": [{"value": "", "label": "Unassigned"}] + [{"value": s.id, "label": s.name} for s in staff]},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(STATUSES), "value": "Open", "required": True},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/api/maintenance")
@login_required
def list_maintenance():
    items = MaintenanceRequest.query.order_by(MaintenanceRequest.report_date.desc()).limit(500)
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/maintenance")
@login_required
def create_maintenance():
    try:
        item = MaintenanceRequest(reported_by_id=current_user.id)
        _apply(item, json_data())
        db.session.add(item)
        db.session.flush()
        record_activity("Reported maintenance issue", "MaintenanceRequest", item.id, item.issue_title)
        db.session.commit()
        return jsonify({"item": serialize(item)}), 201
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.put("/api/maintenance/<int:item_id>")
@login_required
def update_maintenance(item_id: int):
    item = db.get_or_404(MaintenanceRequest, item_id)
    try:
        previous = item.status
        _apply(item, json_data())
        if item.status == "Completed" and previous != "Completed":
            item.completion_date = datetime.now(timezone.utc)
        elif item.status != "Completed":
            item.completion_date = None
        record_activity("Updated maintenance issue", "MaintenanceRequest", item.id, item.issue_title)
        db.session.commit()
        return jsonify({"item": serialize(item)})
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


def _apply(item: MaintenanceRequest, data: dict) -> None:
    zone = db.session.get(ParkZone, int(data.get("zone_id", 0)))
    if not zone:
        raise ValidationError("A valid park zone is required.")
    item.zone = zone
    item.issue_title = require_text(data, "issue_title", max_length=160)
    item.description = require_text(data, "description", max_length=3000)
    item.priority = one_of(data, "priority", PRIORITIES, default="Medium")
    item.status = one_of(data, "status", STATUSES, default="Open")
    facility_id = data.get("facility_id")
    item.facility = db.session.get(Facility, int(facility_id)) if facility_id else None
    if facility_id and not item.facility:
        raise ValidationError("Invalid facility.")
    staff_id = data.get("assigned_staff_id")
    item.assigned_staff = db.session.get(Staff, int(staff_id)) if staff_id else None
    if staff_id and not item.assigned_staff:
        raise ValidationError("Invalid assigned staff member.")

