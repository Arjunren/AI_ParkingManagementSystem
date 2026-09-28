from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Facility, ParkZone
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.auth import admin_required
from app.utils.validation import ValidationError, iso_date, one_of, optional_text, positive_int, require_text


bp = Blueprint("facilities", __name__)
ZONE_STATUSES = {"Open", "Closed", "Maintenance", "Restricted"}
FACILITY_STATUSES = {"Available", "Reserved", "Under Maintenance", "Closed"}


def serialize_zone(item: ParkZone) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "max_capacity": item.max_capacity,
        "current_visitors": item.current_visitors,
        "status": item.status,
        "facility_count": len(item.facilities),
    }


def serialize_facility(item: Facility) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "facility_type": item.facility_type,
        "zone_id": item.zone_id,
        "zone": item.zone.name,
        "description": item.description,
        "capacity": item.capacity,
        "status": item.status,
        "last_inspection_date": item.last_inspection_date.isoformat() if item.last_inspection_date else None,
        "next_inspection_date": item.next_inspection_date.isoformat() if item.next_inspection_date else None,
    }


@bp.get("/zones")
@login_required
def zones_page():
    config = page_config(
        title="Park Zones",
        subtitle="Capacity, occupancy, and operating status across the park.",
        endpoint="/api/zones",
        admin_only=True,
        columns=[
            {"key": "name", "label": "Zone"},
            {"key": "max_capacity", "label": "Capacity"},
            {"key": "current_visitors", "label": "Current visitors"},
            {"key": "facility_count", "label": "Facilities"},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "name", "label": "Zone name", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "textarea"},
            {"name": "max_capacity", "label": "Maximum capacity", "type": "number", "min": 0, "required": True},
            {"name": "current_visitors", "label": "Current visitors", "type": "number", "min": 0, "required": True},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(ZONE_STATUSES), "value": "Open", "required": True},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/facilities")
@login_required
def facilities_page():
    zones = ParkZone.query.order_by(ParkZone.name).all()
    config = page_config(
        title="Facility Management",
        subtitle="Track availability, capacity, and inspection dates.",
        endpoint="/api/facilities",
        columns=[
            {"key": "name", "label": "Facility"},
            {"key": "facility_type", "label": "Type"},
            {"key": "zone", "label": "Zone"},
            {"key": "capacity", "label": "Capacity"},
            {"key": "status", "label": "Status", "badge": True},
            {"key": "next_inspection_date", "label": "Next inspection"},
        ],
        fields=[
            {"name": "name", "label": "Facility name", "type": "text", "required": True},
            {"name": "facility_type", "label": "Facility type", "type": "text", "required": True},
            {"name": "zone_id", "label": "Park zone", "type": "select", "options": [{"value": z.id, "label": z.name} for z in zones], "required": True},
            {"name": "description", "label": "Description", "type": "textarea"},
            {"name": "capacity", "label": "Capacity", "type": "number", "min": 0, "required": True},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(FACILITY_STATUSES), "value": "Available", "required": True},
            {"name": "last_inspection_date", "label": "Last inspection", "type": "date"},
            {"name": "next_inspection_date", "label": "Next inspection", "type": "date"},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/api/zones")
@login_required
def list_zones():
    return jsonify({"items": [serialize_zone(item) for item in ParkZone.query.order_by(ParkZone.name)]})


@bp.post("/api/zones")
@admin_required
def create_zone():
    try:
        data = json_data()
        item = ParkZone()
        _apply_zone(item, data)
        db.session.add(item)
        db.session.flush()
        record_activity("Created park zone", "ParkZone", item.id, item.name)
        db.session.commit()
        return jsonify({"item": serialize_zone(item)}), 201
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)


@bp.put("/api/zones/<int:item_id>")
@admin_required
def update_zone(item_id: int):
    item = db.get_or_404(ParkZone, item_id)
    try:
        _apply_zone(item, json_data())
        record_activity("Updated park zone", "ParkZone", item.id, item.name)
        db.session.commit()
        return jsonify({"item": serialize_zone(item)})
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)


def _apply_zone(item: ParkZone, data: dict) -> None:
    item.name = require_text(data, "name", max_length=120)
    item.description = optional_text(data, "description", max_length=2000)
    item.max_capacity = positive_int(data, "max_capacity", minimum=0)
    item.current_visitors = positive_int(data, "current_visitors", minimum=0)
    if item.max_capacity and item.current_visitors > item.max_capacity:
        raise ValidationError("Current visitors cannot exceed maximum capacity.")
    item.status = one_of(data, "status", ZONE_STATUSES, default="Open")


@bp.get("/api/facilities")
@login_required
def list_facilities():
    return jsonify({"items": [serialize_facility(item) for item in Facility.query.order_by(Facility.name)]})


@bp.post("/api/facilities")
@login_required
def create_facility():
    try:
        item = Facility()
        _apply_facility(item, json_data())
        db.session.add(item)
        db.session.flush()
        record_activity("Created facility", "Facility", item.id, item.name)
        db.session.commit()
        return jsonify({"item": serialize_facility(item)}), 201
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.put("/api/facilities/<int:item_id>")
@login_required
def update_facility(item_id: int):
    item = db.get_or_404(Facility, item_id)
    try:
        _apply_facility(item, json_data())
        record_activity("Updated facility", "Facility", item.id, item.name)
        db.session.commit()
        return jsonify({"item": serialize_facility(item)})
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.delete("/api/facilities/<int:item_id>")
@admin_required
def delete_facility(item_id: int):
    item = db.get_or_404(Facility, item_id)
    if item.reservations:
        return jsonify({"error": "Facilities with reservation history cannot be deleted."}), 409
    record_activity("Deleted facility", "Facility", item.id, item.name)
    db.session.delete(item)
    db.session.commit()
    return "", 204


def _apply_facility(item: Facility, data: dict) -> None:
    item.name = require_text(data, "name", max_length=120)
    item.facility_type = require_text(data, "facility_type", max_length=80)
    zone = db.session.get(ParkZone, int(data.get("zone_id", 0)))
    if not zone:
        raise ValidationError("A valid park zone is required.")
    item.zone = zone
    item.description = optional_text(data, "description", max_length=2000)
    item.capacity = positive_int(data, "capacity", minimum=0)
    item.status = one_of(data, "status", FACILITY_STATUSES, default="Available")
    item.last_inspection_date = iso_date(data, "last_inspection_date") if data.get("last_inspection_date") else None
    item.next_inspection_date = iso_date(data, "next_inspection_date") if data.get("next_inspection_date") else None
    if item.last_inspection_date and item.next_inspection_date and item.next_inspection_date < item.last_inspection_date:
        raise ValidationError("Next inspection cannot be before the last inspection.")

