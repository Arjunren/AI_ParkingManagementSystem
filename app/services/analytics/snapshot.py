from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models import (
    Facility,
    IncidentReport,
    MaintenanceRequest,
    ParkZone,
    Reservation,
    Ticket,
    Visitor,
    VisitorFeedback,
)


def _day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def build_operational_snapshot(target: date | None = None) -> dict:
    target = target or date.today()
    start, end = _day_bounds(target)

    visitors = Visitor.query.filter(Visitor.entry_time >= start, Visitor.entry_time < end).all()
    visitor_count = sum(visitor.guest_count for visitor in visitors)
    currently_inside = sum(
        visitor.guest_count
        for visitor in Visitor.query.filter(Visitor.exit_time.is_(None)).all()
    )
    hourly = Counter()
    for visitor in visitors:
        hourly[f"{visitor.entry_time.hour:02d}:00"] += visitor.guest_count

    zones = ParkZone.query.order_by(ParkZone.name).all()
    zone_data = []
    for zone in zones:
        occupancy = (
            round((zone.current_visitors / zone.max_capacity) * 100, 1)
            if zone.max_capacity
            else 0
        )
        zone_data.append(
            {
                "name": zone.name,
                "status": zone.status,
                "capacity": zone.max_capacity,
                "visitor_count": zone.current_visitors,
                "occupancy_percent": occupancy,
                "facility_count": len(zone.facilities),
            }
        )

    facilities = Facility.query.order_by(Facility.name).all()
    facility_data = [
        {
            "name": facility.name,
            "type": facility.facility_type,
            "zone": facility.zone.name,
            "status": facility.status,
            "capacity": facility.capacity,
            "last_inspection": facility.last_inspection_date.isoformat()
            if facility.last_inspection_date
            else None,
            "next_inspection": facility.next_inspection_date.isoformat()
            if facility.next_inspection_date
            else None,
        }
        for facility in facilities
    ]

    reservations = Reservation.query.filter(Reservation.reservation_date == target).all()
    reservation_counts = Counter(reservation.facility.name for reservation in reservations)

    maintenance = MaintenanceRequest.query.filter(
        MaintenanceRequest.report_date >= start,
        MaintenanceRequest.report_date < end,
    ).all()
    maintenance_data = [
        {
            "facility": item.facility.name if item.facility else None,
            "zone": item.zone.name,
            "issue": item.issue_title,
            "priority": item.priority,
            "status": item.status,
        }
        for item in maintenance
    ]

    incidents = IncidentReport.query.filter(IncidentReport.incident_date == target).all()
    incident_data = [
        {
            "type": item.incident_type,
            "zone": item.zone.name,
            "severity": item.severity,
            "status": item.status,
        }
        for item in incidents
    ]

    feedback = VisitorFeedback.query.filter(
        VisitorFeedback.feedback_date >= start,
        VisitorFeedback.feedback_date < end,
    ).all()
    feedback_categories = Counter(item.category for item in feedback)
    average_rating = round(sum(item.rating for item in feedback) / len(feedback), 2) if feedback else None

    tickets = Ticket.query.filter(Ticket.entry_timestamp >= start, Ticket.entry_timestamp < end).all()
    ticket_revenue = sum(
        (ticket.entrance_fee for ticket in tickets if ticket.payment_status == "Paid"),
        Decimal("0.00"),
    )

    return {
        "date": target.isoformat(),
        "visitors": {
            "count": visitor_count,
            "currently_inside": currently_inside,
            "entry_by_hour": [
                {"hour": hour, "count": count}
                for hour, count in sorted(hourly.items())
            ],
        },
        "zones": zone_data,
        "facilities": facility_data,
        "reservations": {
            "count": len(reservations),
            "by_facility": [
                {"facility": name, "count": count}
                for name, count in reservation_counts.most_common()
            ],
        },
        "maintenance_reports": maintenance_data,
        "incidents": incident_data,
        "feedback": {
            "count": len(feedback),
            "average_rating": average_rating,
            "categories": [
                {"category": category, "count": count}
                for category, count in feedback_categories.most_common()
            ],
        },
        "tickets": {
            "sold": len(tickets),
            "paid": sum(1 for ticket in tickets if ticket.payment_status == "Paid"),
            "revenue": str(ticket_revenue),
            "active": sum(1 for ticket in tickets if ticket.status == "Active"),
        },
    }


def snapshot_summary(snapshot: dict) -> dict:
    return {
        "date": snapshot.get("date"),
        "visitors": snapshot.get("visitors", {}).get("count", 0),
        "zones": len(snapshot.get("zones", [])),
        "facilities": len(snapshot.get("facilities", [])),
        "reservations": snapshot.get("reservations", {}).get("count", 0),
        "maintenance_reports": len(snapshot.get("maintenance_reports", [])),
        "incidents": len(snapshot.get("incidents", [])),
        "feedback": snapshot.get("feedback", {}).get("count", 0),
        "tickets": snapshot.get("tickets", {}).get("sold", 0),
    }

