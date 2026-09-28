from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import Facility, ParkZone, VisitorFeedback
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.validation import ValidationError, one_of, optional_text, positive_int, require_text


bp = Blueprint("feedback", __name__)
CATEGORIES = {"Cleanliness", "Facilities", "Staff", "Safety", "Entrance", "Parking", "Environment", "Other"}
STATUSES = {"New", "Reviewed", "Resolved", "Archived"}


def serialize(item: VisitorFeedback) -> dict:
    return {
        "id": item.id,
        "rating": item.rating,
        "category": item.category,
        "comment": item.comment,
        "feedback_date": item.feedback_date.isoformat(),
        "facility_id": item.facility_id,
        "facility": item.facility.name if item.facility else "—",
        "zone_id": item.zone_id,
        "zone": item.zone.name if item.zone else "—",
        "status": item.status,
        "is_anonymous": item.is_anonymous,
    }


@bp.get("/feedback")
@login_required
def page():
    facilities = Facility.query.order_by(Facility.name).all()
    zones = ParkZone.query.order_by(ParkZone.name).all()
    config = page_config(
        title="Visitor Feedback",
        subtitle="Review ratings and comments without collecting unnecessary identity data.",
        endpoint="/api/feedback",
        columns=[
            {"key": "rating", "label": "Rating"},
            {"key": "category", "label": "Category"},
            {"key": "comment", "label": "Comment"},
            {"key": "zone", "label": "Zone"},
            {"key": "facility", "label": "Facility"},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "rating", "label": "Rating (1–5)", "type": "number", "min": 1, "max": 5, "required": True},
            {"name": "category", "label": "Category", "type": "select", "options": sorted(CATEGORIES), "required": True},
            {"name": "comment", "label": "Comment", "type": "textarea", "required": True},
            {"name": "zone_id", "label": "Related zone", "type": "select", "options": [{"value": "", "label": "None"}] + [{"value": z.id, "label": z.name} for z in zones]},
            {"name": "facility_id", "label": "Related facility", "type": "select", "options": [{"value": "", "label": "None"}] + [{"value": f.id, "label": f.name} for f in facilities]},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(STATUSES), "value": "New", "required": True},
            {"name": "is_anonymous", "label": "Anonymous", "type": "checkbox", "value": True},
        ],
    )
    return render_template("manage.html", page_config=config)


@bp.route("/feedback/submit", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def public_submit():
    zones = ParkZone.query.filter_by(status="Open").order_by(ParkZone.name).all()
    if request.method == "POST":
        try:
            data = request.form.to_dict()
            item = VisitorFeedback(
                rating=positive_int(data, "rating", minimum=1, maximum=5),
                category=one_of(data, "category", CATEGORIES),
                comment=require_text(data, "comment", max_length=2000),
                zone=db.session.get(ParkZone, int(data["zone_id"])) if data.get("zone_id") else None,
                is_anonymous=True,
            )
            db.session.add(item)
            db.session.commit()
            flash("Thank you. Your feedback has been recorded.", "success")
            return redirect(url_for("feedback.public_submit"))
        except (ValidationError, ValueError, TypeError):
            db.session.rollback()
            flash("Please check the feedback form and try again.", "error")
    return render_template("public_feedback.html", categories=sorted(CATEGORIES), zones=zones)


@bp.get("/api/feedback")
@login_required
def list_feedback():
    items = VisitorFeedback.query.order_by(VisitorFeedback.feedback_date.desc()).limit(500)
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/feedback")
@login_required
def create_feedback():
    try:
        item = VisitorFeedback()
        _apply(item, json_data())
        db.session.add(item)
        db.session.flush()
        record_activity("Recorded visitor feedback", "VisitorFeedback", item.id, item.category)
        db.session.commit()
        return jsonify({"item": serialize(item)}), 201
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


@bp.put("/api/feedback/<int:item_id>")
@login_required
def update_feedback(item_id: int):
    item = db.get_or_404(VisitorFeedback, item_id)
    try:
        _apply(item, json_data())
        record_activity("Updated visitor feedback", "VisitorFeedback", item.id, item.category)
        db.session.commit()
        return jsonify({"item": serialize(item)})
    except (ValidationError, IntegrityError, ValueError, TypeError) as exc:
        return validation_error(exc)


def _apply(item: VisitorFeedback, data: dict) -> None:
    item.rating = positive_int(data, "rating", minimum=1, maximum=5)
    item.category = one_of(data, "category", CATEGORIES)
    item.comment = require_text(data, "comment", max_length=2000)
    item.status = one_of(data, "status", STATUSES, default="New")
    item.is_anonymous = bool(data.get("is_anonymous", True))
    zone_id = data.get("zone_id")
    facility_id = data.get("facility_id")
    item.zone = db.session.get(ParkZone, int(zone_id)) if zone_id else None
    item.facility = db.session.get(Facility, int(facility_id)) if facility_id else None
    if zone_id and not item.zone:
        raise ValidationError("Invalid park zone.")
    if facility_id and not item.facility:
        raise ValidationError("Invalid facility.")

