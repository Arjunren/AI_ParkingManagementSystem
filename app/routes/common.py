from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.utils.validation import ValidationError


def json_data() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("A JSON object is required.")
    return data


def json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def validation_error(exc: Exception):
    db.session.rollback()
    if isinstance(exc, IntegrityError):
        return jsonify({"error": "That record conflicts with existing data."}), 409
    return jsonify({"error": str(exc)}), 400


def page_config(
    *, title: str, subtitle: str, endpoint: str, columns: list[dict], fields: list[dict], admin_only=False
) -> dict:
    return {
        "title": title,
        "subtitle": subtitle,
        "endpoint": endpoint,
        "columns": columns,
        "fields": fields,
        "admin_only": admin_only,
    }

