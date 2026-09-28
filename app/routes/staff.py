from flask import Blueprint, jsonify, render_template
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ParkZone, Staff, User
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.auth import admin_required
from app.utils.validation import ValidationError, one_of, optional_text, require_text


bp = Blueprint("staff", __name__)
ACCOUNT_STATUSES = {"Active", "Inactive"}
ROLES = {"Administrator", "Park Staff"}


def serialize_staff(item: Staff) -> dict:
    return {
        "id": item.id,
        "employee_id": item.employee_id,
        "name": item.name,
        "position": item.position,
        "contact_info": item.contact_info,
        "assigned_zone_id": item.assigned_zone_id,
        "assigned_zone": item.assigned_zone.name if item.assigned_zone else "Unassigned",
        "shift": item.shift,
        "account_status": item.account_status,
    }


@bp.get("/staff")
@admin_required
def page():
    zones = ParkZone.query.order_by(ParkZone.name).all()
    config = page_config(
        title="Staff Management",
        subtitle="Maintain employee assignments, shifts, and account status.",
        endpoint="/api/staff",
        admin_only=True,
        columns=[
            {"key": "employee_id", "label": "Employee ID"},
            {"key": "name", "label": "Name"},
            {"key": "position", "label": "Position"},
            {"key": "assigned_zone", "label": "Zone"},
            {"key": "shift", "label": "Shift"},
            {"key": "account_status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "employee_id", "label": "Employee ID", "type": "text", "required": True},
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "position", "label": "Position", "type": "text", "required": True},
            {"name": "contact_info", "label": "Contact information", "type": "text"},
            {"name": "assigned_zone_id", "label": "Assigned zone", "type": "select", "options": [{"value": "", "label": "Unassigned"}] + [{"value": z.id, "label": z.name} for z in zones]},
            {"name": "shift", "label": "Shift", "type": "text", "required": True},
            {"name": "account_status", "label": "Status", "type": "select", "options": sorted(ACCOUNT_STATUSES), "value": "Active", "required": True},
        ],
    )
    return render_template("manage.html", page_config=config, show_users=True)


@bp.get("/api/staff")
@admin_required
def list_staff():
    return jsonify({"items": [serialize_staff(item) for item in Staff.query.order_by(Staff.name)]})


@bp.post("/api/staff")
@admin_required
def create_staff():
    try:
        item = Staff()
        _apply_staff(item, json_data())
        db.session.add(item)
        db.session.flush()
        record_activity("Created staff record", "Staff", item.id, item.employee_id)
        db.session.commit()
        return jsonify({"item": serialize_staff(item)}), 201
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.put("/api/staff/<int:item_id>")
@admin_required
def update_staff(item_id: int):
    item = db.get_or_404(Staff, item_id)
    try:
        _apply_staff(item, json_data())
        record_activity("Updated staff record", "Staff", item.id, item.employee_id)
        db.session.commit()
        return jsonify({"item": serialize_staff(item)})
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


def _apply_staff(item: Staff, data: dict) -> None:
    item.employee_id = require_text(data, "employee_id", max_length=40)
    item.name = require_text(data, "name", max_length=120)
    item.position = require_text(data, "position", max_length=120)
    item.contact_info = optional_text(data, "contact_info", max_length=180)
    item.shift = require_text(data, "shift", max_length=80)
    item.account_status = one_of(data, "account_status", ACCOUNT_STATUSES, default="Active")
    zone_id = data.get("assigned_zone_id")
    item.assigned_zone = db.session.get(ParkZone, int(zone_id)) if zone_id else None
    if zone_id and not item.assigned_zone:
        raise ValidationError("Invalid assigned zone.")


@bp.get("/api/users")
@admin_required
def list_users():
    return jsonify(
        {
            "items": [
                {"id": u.id, "username": u.username, "role": u.role, "active": u.is_active_account}
                for u in User.query.order_by(User.username)
            ]
        }
    )


@bp.post("/api/users")
@admin_required
def create_user():
    try:
        data = json_data()
        username = require_text(data, "username", max_length=80).lower()
        password = require_text(data, "password", max_length=200)
        if len(username) < 3 or len(password) < 12:
            raise ValidationError("Username must be 3+ characters and password 12+ characters.")
        user = User(
            username=username,
            role=one_of(data, "role", ROLES, default="Park Staff"),
            is_active_account=bool(data.get("active", True)),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        record_activity("Created user account", "User", user.id, user.username)
        db.session.commit()
        return jsonify({"item": {"id": user.id, "username": user.username, "role": user.role, "active": user.is_active_account}}), 201
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)

