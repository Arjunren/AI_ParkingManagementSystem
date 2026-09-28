from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import Visitor
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.validation import (
    ValidationError,
    iso_datetime,
    one_of,
    optional_text,
    positive_int,
    require_text,
)


bp = Blueprint("visitors", __name__)
CATEGORIES = {"Adult", "Child", "Senior Citizen", "PWD", "Student", "Group"}


def serialize(item: Visitor) -> dict:
    return {
        "id": item.id,
        "display_name": item.display_name,
        "category": item.category,
        "contact_info": item.contact_info,
        "guest_count": item.guest_count,
        "entry_time": item.entry_time.isoformat(),
        "exit_time": item.exit_time.isoformat() if item.exit_time else None,
        "status": "Exited" if item.exit_time else "Inside",
    }


@bp.get("/visitors")
@login_required
def page():
    config = page_config(
        title="Visitor Management",
        subtitle="Register walk-ins and track current park attendance.",
        endpoint="/api/visitors",
        columns=[
            {"key": "display_name", "label": "Visitor"},
            {"key": "category", "label": "Category"},
            {"key": "guest_count", "label": "Guests"},
            {"key": "entry_time", "label": "Entry"},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "display_name", "label": "Display name", "type": "text", "required": True},
            {"name": "category", "label": "Category", "type": "select", "options": sorted(CATEGORIES), "required": True},
            {"name": "contact_info", "label": "Contact (optional)", "type": "text"},
            {"name": "guest_count", "label": "Number of guests", "type": "number", "min": 1, "value": 1, "required": True},
            {"name": "entry_time", "label": "Entry time", "type": "datetime-local"},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.get("/api/visitors")
@login_required
def list_visitors():
    items = Visitor.query.order_by(Visitor.entry_time.desc()).limit(500).all()
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/visitors")
@login_required
@limiter.limit("120 per hour")
def create_visitor():
    try:
        data = json_data()
        visitor = Visitor(
            display_name=require_text(data, "display_name", max_length=120),
            category=one_of(data, "category", CATEGORIES),
            contact_info=optional_text(data, "contact_info", max_length=180),
            guest_count=positive_int(data, "guest_count", minimum=1, maximum=500),
            entry_time=iso_datetime(data, "entry_time", required=False) or datetime.now(timezone.utc),
            created_by_id=current_user.id,
        )
        db.session.add(visitor)
        db.session.flush()
        record_activity("Registered visitor", "Visitor", visitor.id, visitor.category)
        db.session.commit()
        return jsonify({"item": serialize(visitor)}), 201
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)


@bp.put("/api/visitors/<int:item_id>")
@login_required
def update_visitor(item_id: int):
    visitor = db.get_or_404(Visitor, item_id)
    try:
        data = json_data()
        visitor.display_name = require_text(data, "display_name", max_length=120)
        visitor.category = one_of(data, "category", CATEGORIES)
        visitor.contact_info = optional_text(data, "contact_info", max_length=180)
        visitor.guest_count = positive_int(data, "guest_count", minimum=1, maximum=500)
        if data.get("entry_time"):
            visitor.entry_time = iso_datetime(data, "entry_time")
        record_activity("Updated visitor", "Visitor", visitor.id, visitor.category)
        db.session.commit()
        return jsonify({"item": serialize(visitor)})
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)


@bp.post("/api/visitors/<int:item_id>/exit")
@login_required
def exit_visitor(item_id: int):
    visitor = db.get_or_404(Visitor, item_id)
    visitor.exit_time = datetime.now(timezone.utc)
    record_activity("Recorded visitor exit", "Visitor", visitor.id, visitor.category)
    db.session.commit()
    return jsonify({"item": serialize(visitor)})


@bp.delete("/api/visitors/<int:item_id>")
@login_required
def delete_visitor(item_id: int):
    visitor = db.get_or_404(Visitor, item_id)
    if visitor.tickets:
        return jsonify({"error": "Visitors with tickets cannot be deleted."}), 409
    record_activity("Deleted visitor", "Visitor", visitor.id, visitor.category)
    db.session.delete(visitor)
    db.session.commit()
    return "", 204

