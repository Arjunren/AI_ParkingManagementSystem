import csv
import io
import json
from datetime import date, datetime, time, timedelta, timezone

from flask import Blueprint, Response, jsonify, render_template, request

from app.models import (
    AIRecommendation,
    Facility,
    IncidentReport,
    MaintenanceRequest,
    Reservation,
    Ticket,
    Visitor,
    VisitorFeedback,
)
from app.utils.auth import admin_required


bp = Blueprint("reports", __name__)
REPORTS = {
    "visitors": ("Visitor Report", Visitor, "entry_time"),
    "tickets": ("Ticket Sales Report", Ticket, "entry_timestamp"),
    "reservations": ("Reservation Report", Reservation, "reservation_date"),
    "facilities": ("Facility Usage Report", Facility, None),
    "maintenance": ("Maintenance Report", MaintenanceRequest, "report_date"),
    "incidents": ("Incident Report", IncidentReport, "incident_date"),
    "feedback": ("Visitor Feedback Report", VisitorFeedback, "feedback_date"),
    "recommendations": ("AI Recommendation Report", AIRecommendation, "generated_at"),
}


@bp.get("/reports")
@admin_required
def page():
    return render_template("reports.html", reports={key: value[0] for key, value in REPORTS.items()})


def _parse_dates():
    try:
        start = date.fromisoformat(request.args.get("start", date.today().replace(day=1).isoformat()))
        end = date.fromisoformat(request.args.get("end", date.today().isoformat()))
    except ValueError:
        raise ValueError("Dates must use YYYY-MM-DD.")
    if end < start or (end - start).days > 366:
        raise ValueError("Select a valid range of up to 366 days.")
    return start, end


def _records(report_type: str):
    if report_type not in REPORTS:
        raise KeyError(report_type)
    title, model, field_name = REPORTS[report_type]
    query = model.query
    start, end = _parse_dates()
    if field_name:
        field = getattr(model, field_name)
        if field.type.python_type is datetime:
            start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
            end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
            query = query.filter(field >= start_dt, field < end_dt)
        else:
            query = query.filter(field >= start, field <= end)
    return title, query.order_by(model.id.desc()).limit(5000).all(), start, end


def _serialize(record):
    data = {}
    excluded = {"password_hash", "contact_info", "customer_name", "display_name"}
    for column in record.__table__.columns:
        if column.name in excluded:
            continue
        value = getattr(record, column.name)
        if isinstance(value, (datetime, date, time)):
            value = value.isoformat()
        elif hasattr(value, "as_tuple"):
            value = str(value)
        data[column.name] = value
    return data


@bp.get("/api/reports/<report_type>")
@admin_required
def report_data(report_type: str):
    try:
        title, records, start, end = _records(report_type)
    except KeyError:
        return jsonify({"error": "Unknown report type."}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    rows = [_serialize(record) for record in records]
    return jsonify({"title": title, "start": start.isoformat(), "end": end.isoformat(), "count": len(rows), "items": rows})


@bp.get("/reports/<report_type>/export.<format>")
@admin_required
def export(report_type: str, format: str):
    try:
        title, records, start, end = _records(report_type)
    except KeyError:
        return jsonify({"error": "Unknown report type."}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    rows = [_serialize(record) for record in records]
    filename = f"parksmart-{report_type}-{start}-{end}"
    if format == "json":
        return Response(json.dumps(rows, indent=2), mimetype="application/json", headers={"Content-Disposition": f"attachment; filename={filename}.json"})
    if format == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}.csv"})
    if format == "html":
        return render_template("report_print.html", title=title, rows=rows, start=start, end=end)
    return jsonify({"error": "Unsupported export format."}), 400

