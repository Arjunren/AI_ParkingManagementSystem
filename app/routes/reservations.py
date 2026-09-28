from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Facility, Reservation
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.validation import (
    ValidationError,
    iso_date,
    iso_time,
    one_of,
    optional_text,
    positive_int,
    require_text,
)


bp = Blueprint("reservations", __name__)
STATUSES = {"Pending", "Confirmed", "Completed", "Cancelled"}
PAYMENT_STATUSES = {"Pending", "Paid", "Waived", "Refunded"}


def serialize(item: Reservation) -> dict:
    return {
        "id": item.id,
        "reservation_number": item.reservation_number,
        "customer_name": item.customer_name,
        "contact_info": item.contact_info,
        "facility_id": item.facility_id,
        "facility": item.facility.name,
        "reservation_date": item.reservation_date.isoformat(),
        "start_time": item.start_time.strftime("%H:%M"),
        "end_time": item.end_time.strftime("%H:%M"),
        "guest_count": item.guest_count,
        "payment_status": item.payment_status,
        "status": item.status,
    }


@bp.get("/reservations")
@login_required
def page():
    facilities = Facility.query.order_by(Facility.name).all()
    config = page_config(
        title="Facility Reservations",
        subtitle="Schedule eligible facilities with automatic overlap prevention.",
        endpoint="/api/reservations",
        columns=[
            {"key": "reservation_number", "label": "Reservation"},
            {"key": "customer_name", "label": "Customer"},
            {"key": "facility", "label": "Facility"},
            {"key": "reservation_date", "label": "Date"},
            {"key": "start_time", "label": "Start"},
            {"key": "end_time", "label": "End"},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "customer_name", "label": "Customer name", "type": "text", "required": True},
            {"name": "contact_info", "label": "Contact information", "type": "text"},
            {"name": "facility_id", "label": "Facility", "type": "select", "options": [{"value": f.id, "label": f"{f.name} — {f.zone.name}"} for f in facilities], "required": True},
            {"name": "reservation_date", "label": "Date", "type": "date", "required": True},
            {"name": "start_time", "label": "Start time", "type": "time", "required": True},
            {"name": "end_time", "label": "End time", "type": "time", "required": True},
            {"name": "guest_count", "label": "Guests", "type": "number", "min": 1, "required": True},
            {"name": "payment_status", "label": "Payment", "type": "select", "options": sorted(PAYMENT_STATUSES), "value": "Pending", "required": True},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(STATUSES), "value": "Pending", "required": True},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/api/reservations")
@login_required
def list_reservations():
    items = Reservation.query.order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc()).limit(500)
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/reservations")
@login_required
def create_reservation():
    try:
        item = Reservation(
            reservation_number=f"RES-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}"
        )
        _apply(item, json_data())
        _ensure_available(item)
        db.session.add(item)
        db.session.flush()
        record_activity("Created reservation", "Reservation", item.id, item.reservation_number)
        db.session.commit()
        return jsonify({"item": serialize(item)}), 201
    except (ValidationError, IntegrityError, TypeError, ValueError) as exc:
        return validation_error(exc)


@bp.put("/api/reservations/<int:item_id>")
@login_required
def update_reservation(item_id: int):
    item = db.get_or_404(Reservation, item_id)
    try:
        _apply(item, json_data())
        _ensure_available(item)
        record_activity("Updated reservation", "Reservation", item.id, item.reservation_number)
        db.session.commit()
        return jsonify({"item": serialize(item)})
    except (ValidationError, IntegrityError, TypeError, ValueError) as exc:
        return validation_error(exc)


@bp.delete("/api/reservations/<int:item_id>")
@login_required
def delete_reservation(item_id: int):
    item = db.get_or_404(Reservation, item_id)
    record_activity("Deleted reservation", "Reservation", item.id, item.reservation_number)
    db.session.delete(item)
    db.session.commit()
    return "", 204


def _apply(item: Reservation, data: dict) -> None:
    facility = db.session.get(Facility, int(data.get("facility_id", 0)))
    if not facility:
        raise ValidationError("A valid facility is required.")
    item.customer_name = require_text(data, "customer_name", max_length=120)
    item.contact_info = optional_text(data, "contact_info", max_length=180)
    # Set the foreign key directly so overlap validation can query it before
    # this new object is added to the session.
    item.facility_id = facility.id
    item.reservation_date = iso_date(data, "reservation_date")
    item.start_time = iso_time(data, "start_time")
    item.end_time = iso_time(data, "end_time")
    if item.end_time <= item.start_time:
        raise ValidationError("End time must be later than start time.")
    item.guest_count = positive_int(data, "guest_count", minimum=1, maximum=5000)
    if facility.capacity and item.guest_count > facility.capacity:
        raise ValidationError("Guest count exceeds the facility capacity.")
    item.payment_status = one_of(data, "payment_status", PAYMENT_STATUSES, default="Pending")
    item.status = one_of(data, "status", STATUSES, default="Pending")


def _ensure_available(item: Reservation) -> None:
    if item.status == "Cancelled":
        return
    overlap = Reservation.query.filter(
        Reservation.facility_id == item.facility_id,
        Reservation.reservation_date == item.reservation_date,
        Reservation.status.in_(["Pending", "Confirmed"]),
        Reservation.start_time < item.end_time,
        Reservation.end_time > item.start_time,
    )
    if item.id:
        overlap = overlap.filter(Reservation.id != item.id)
    if overlap.first():
        raise ValidationError("This facility is already booked for the selected time.")
