from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from flask_login import UserMixin
from sqlalchemy import Index, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="Park Staff", index=True)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return self.is_active_account

    @property
    def is_admin(self) -> bool:
        return self.role == "Administrator"


class ParkZone(TimestampMixin, db.Model):
    __tablename__ = "park_zones"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False, default="")
    max_capacity = db.Column(db.Integer, nullable=False, default=0)
    current_visitors = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="Open", index=True)


class Staff(TimestampMixin, db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(40), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(120), nullable=False)
    contact_info = db.Column(db.String(180), nullable=False, default="")
    assigned_zone_id = db.Column(db.Integer, db.ForeignKey("park_zones.id"))
    shift = db.Column(db.String(80), nullable=False, default="Day")
    account_status = db.Column(db.String(32), nullable=False, default="Active")

    assigned_zone = db.relationship("ParkZone", backref="assigned_staff")


class Visitor(TimestampMixin, db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False, default="Walk-in Visitor")
    category = db.Column(db.String(32), nullable=False, index=True)
    contact_info = db.Column(db.String(180), nullable=False, default="")
    guest_count = db.Column(db.Integer, nullable=False, default=1)
    entry_time = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    exit_time = db.Column(db.DateTime(timezone=True))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_by = db.relationship("User", foreign_keys=[created_by_id])


class TicketPrice(TimestampMixin, db.Model):
    __tablename__ = "ticket_prices"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(32), nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)


class Ticket(TimestampMixin, db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False)
    visitor_category = db.Column(db.String(32), nullable=False)
    entrance_fee = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(32), nullable=False, default="Pending")
    entry_timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    status = db.Column(db.String(32), nullable=False, default="Active", index=True)

    visitor = db.relationship("Visitor", backref=db.backref("tickets", lazy=True))


class Facility(TimestampMixin, db.Model):
    __tablename__ = "facilities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    facility_type = db.Column(db.String(80), nullable=False, index=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("park_zones.id"), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    capacity = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="Available", index=True)
    last_inspection_date = db.Column(db.Date)
    next_inspection_date = db.Column(db.Date)

    zone = db.relationship("ParkZone", backref=db.backref("facilities", lazy=True))


class Reservation(TimestampMixin, db.Model):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservation_slot", "facility_id", "reservation_date", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reservation_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    contact_info = db.Column(db.String(180), nullable=False, default="")
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False)
    reservation_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    guest_count = db.Column(db.Integer, nullable=False, default=1)
    payment_status = db.Column(db.String(32), nullable=False, default="Pending")
    status = db.Column(db.String(32), nullable=False, default="Pending", index=True)

    facility = db.relationship("Facility", backref=db.backref("reservations", lazy=True))


class MaintenanceRequest(TimestampMixin, db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"))
    zone_id = db.Column(db.Integer, db.ForeignKey("park_zones.id"), nullable=False)
    issue_title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(32), nullable=False, default="Medium", index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    report_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"))
    status = db.Column(db.String(32), nullable=False, default="Open", index=True)
    completion_date = db.Column(db.DateTime(timezone=True))

    facility = db.relationship("Facility")
    zone = db.relationship("ParkZone")
    reported_by = db.relationship("User")
    assigned_staff = db.relationship("Staff")


class IncidentReport(TimestampMixin, db.Model):
    __tablename__ = "incident_reports"

    id = db.Column(db.Integer, primary_key=True)
    incident_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    incident_type = db.Column(db.String(80), nullable=False, index=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("park_zones.id"), nullable=False)
    incident_date = db.Column(db.Date, nullable=False, index=True)
    incident_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.Text, nullable=False)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    severity = db.Column(db.String(32), nullable=False, default="Low", index=True)
    status = db.Column(db.String(32), nullable=False, default="Open", index=True)
    action_taken = db.Column(db.Text, nullable=False, default="")

    zone = db.relationship("ParkZone")
    reported_by = db.relationship("User")


class VisitorFeedback(TimestampMixin, db.Model):
    __tablename__ = "visitor_feedback"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    comment = db.Column(db.Text, nullable=False)
    feedback_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"))
    zone_id = db.Column(db.Integer, db.ForeignKey("park_zones.id"))
    status = db.Column(db.String(32), nullable=False, default="New", index=True)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=True)

    facility = db.relationship("Facility")
    zone = db.relationship("ParkZone")


class FactoryRun(db.Model):
    __tablename__ = "factory_runs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(32), nullable=False, default="Running", index=True)
    triggered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recommendation_count = db.Column(db.Integer, nullable=False, default=0)
    priority_issue_count = db.Column(db.Integer, nullable=False, default=0)
    iteration_count = db.Column(db.Integer, nullable=False, default=1)
    operational_snapshot = db.Column(db.JSON)
    analysis_output = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    triggered_by = db.relationship("User")


class AgentRun(db.Model):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("factory_run_id", "agent_name", "iteration", name="uq_agent_iteration"),
    )

    id = db.Column(db.Integer, primary_key=True)
    factory_run_id = db.Column(
        db.String(36), db.ForeignKey("factory_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name = db.Column(db.String(80), nullable=False)
    started_at = db.Column(db.DateTime(timezone=True))
    ended_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(32), nullable=False, default="Waiting")
    input_summary = db.Column(db.JSON)
    output_summary = db.Column(db.JSON)
    error = db.Column(db.String(500))
    iteration = db.Column(db.Integer, nullable=False, default=1)

    factory_run = db.relationship(
        "FactoryRun", backref=db.backref("agent_runs", lazy=True, cascade="all, delete-orphan")
    )


class AIRecommendation(db.Model):
    __tablename__ = "ai_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    factory_run_id = db.Column(
        db.String(36), db.ForeignKey("factory_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    priority = db.Column(db.String(32), nullable=False, index=True)
    priority_reason = db.Column(db.String(300), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    recommended_action = db.Column(db.Text, nullable=False)
    related_zone = db.Column(db.String(120), nullable=False, default="")
    related_facility = db.Column(db.String(120), nullable=False, default="")
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    status = db.Column(db.String(32), nullable=False, default="Pending", index=True)
    admin_note = db.Column(db.Text, nullable=False, default="")
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime(timezone=True))

    factory_run = db.relationship(
        "FactoryRun", backref=db.backref("recommendations", lazy=True, cascade="all, delete-orphan")
    )
    reviewed_by = db.relationship("User")


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(120), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80), nullable=False, default="")
    details = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User")

