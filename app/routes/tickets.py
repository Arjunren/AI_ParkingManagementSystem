from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Ticket, TicketPrice, Visitor
from app.routes.common import json_data, page_config, validation_error
from app.utils.activity import record_activity
from app.utils.auth import admin_required
from app.utils.validation import ValidationError, decimal_amount, one_of


bp = Blueprint("tickets", __name__)
PAYMENT_STATUSES = {"Pending", "Paid", "Waived"}
TICKET_STATUSES = {"Active", "Used", "Cancelled"}
CATEGORIES = {"Adult", "Child", "Senior Citizen", "PWD", "Student", "Group"}


def serialize(item: Ticket) -> dict:
    return {
        "id": item.id,
        "ticket_number": item.ticket_number,
        "visitor_id": item.visitor_id,
        "visitor": item.visitor.display_name,
        "visitor_category": item.visitor_category,
        "entrance_fee": float(item.entrance_fee),
        "payment_status": item.payment_status,
        "entry_timestamp": item.entry_timestamp.isoformat(),
        "status": item.status,
    }


@bp.get("/tickets")
@login_required
def page():
    visitors = Visitor.query.order_by(Visitor.entry_time.desc()).limit(300).all()
    config = page_config(
        title="Tickets & Entrance",
        subtitle="Issue entrance tickets using administrator-configured category prices.",
        endpoint="/api/tickets",
        columns=[
            {"key": "ticket_number", "label": "Ticket"},
            {"key": "visitor", "label": "Visitor"},
            {"key": "visitor_category", "label": "Category"},
            {"key": "entrance_fee", "label": "Fee"},
            {"key": "payment_status", "label": "Payment", "badge": True},
            {"key": "status", "label": "Status", "badge": True},
        ],
        fields=[
            {"name": "visitor_id", "label": "Visitor", "type": "select", "options": [{"value": v.id, "label": f"{v.display_name} — {v.category}"} for v in visitors], "required": True},
            {"name": "payment_status", "label": "Payment", "type": "select", "options": sorted(PAYMENT_STATUSES), "required": True},
            {"name": "status", "label": "Status", "type": "select", "options": sorted(TICKET_STATUSES), "value": "Active", "required": True},
        ],
    )
    prices = TicketPrice.query.order_by(TicketPrice.category).all()
    return render_template("manage.html", page_config=config, ticket_prices=prices)


@bp.get("/api/tickets")
@login_required
def list_tickets():
    items = Ticket.query.order_by(Ticket.entry_timestamp.desc()).limit(500).all()
    return jsonify({"items": [serialize(item) for item in items]})


@bp.post("/api/tickets")
@login_required
def create_ticket():
    try:
        data = json_data()
        visitor = db.session.get(Visitor, int(data.get("visitor_id", 0)))
        if not visitor:
            raise ValidationError("A valid visitor is required.")
        price = TicketPrice.query.filter_by(category=visitor.category).first()
        if not price:
            raise ValidationError(f"No ticket price is configured for {visitor.category}.")
        ticket = Ticket(
            ticket_number=f"PS-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}",
            visitor=visitor,
            visitor_category=visitor.category,
            entrance_fee=price.amount,
            payment_status=one_of(data, "payment_status", PAYMENT_STATUSES),
            status=one_of(data, "status", TICKET_STATUSES, default="Active"),
        )
        db.session.add(ticket)
        db.session.flush()
        record_activity("Issued ticket", "Ticket", ticket.id, ticket.ticket_number)
        db.session.commit()
        return jsonify({"item": serialize(ticket)}), 201
    except (ValidationError, IntegrityError, TypeError, ValueError) as exc:
        return validation_error(exc)


@bp.put("/api/tickets/<int:item_id>")
@login_required
def update_ticket(item_id: int):
    ticket = db.get_or_404(Ticket, item_id)
    try:
        data = json_data()
        ticket.payment_status = one_of(data, "payment_status", PAYMENT_STATUSES)
        ticket.status = one_of(data, "status", TICKET_STATUSES)
        record_activity("Updated ticket", "Ticket", ticket.id, ticket.ticket_number)
        db.session.commit()
        return jsonify({"item": serialize(ticket)})
    except ValidationError as exc:
        return validation_error(exc)


@bp.get("/api/ticket-prices")
@login_required
def list_prices():
    return jsonify(
        {"items": [{"id": p.id, "category": p.category, "amount": float(p.amount)} for p in TicketPrice.query.order_by(TicketPrice.category)]}
    )


@bp.post("/api/ticket-prices")
@admin_required
def upsert_price():
    try:
        data = json_data()
        category = one_of(data, "category", CATEGORIES)
        price = TicketPrice.query.filter_by(category=category).first() or TicketPrice(category=category)
        price.amount = decimal_amount(data, "amount")
        db.session.add(price)
        record_activity("Configured ticket price", "TicketPrice", category, f"{price.amount}")
        db.session.commit()
        return jsonify({"item": {"id": price.id, "category": price.category, "amount": float(price.amount)}})
    except (ValidationError, IntegrityError) as exc:
        return validation_error(exc)

