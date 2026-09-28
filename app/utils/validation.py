from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    pass


def require_text(data: dict, key: str, *, max_length: int = 255) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValidationError(f"{key.replace('_', ' ').title()} is required.")
    if len(value) > max_length:
        raise ValidationError(f"{key.replace('_', ' ').title()} is too long.")
    return value


def optional_text(data: dict, key: str, *, max_length: int = 500) -> str:
    value = str(data.get(key, "")).strip()
    if len(value) > max_length:
        raise ValidationError(f"{key.replace('_', ' ').title()} is too long.")
    return value


def one_of(data: dict, key: str, choices: set[str], *, default: str | None = None) -> str:
    value = str(data.get(key, default or "")).strip()
    if value not in choices:
        raise ValidationError(f"Invalid {key.replace('_', ' ')}.")
    return value


def positive_int(data: dict, key: str, *, minimum: int = 0, maximum: int = 100000) -> int:
    try:
        value = int(data.get(key, 0))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be a number.") from exc
    if not minimum <= value <= maximum:
        raise ValidationError(
            f"{key.replace('_', ' ').title()} must be between {minimum} and {maximum}."
        )
    return value


def decimal_amount(data: dict, key: str) -> Decimal:
    try:
        value = Decimal(str(data.get(key, ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be a valid amount.") from exc
    if value < 0 or value > Decimal("1000000"):
        raise ValidationError(f"Invalid {key.replace('_', ' ')}.")
    return value


def iso_date(data: dict, key: str) -> date:
    try:
        return date.fromisoformat(str(data.get(key, "")))
    except ValueError as exc:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be a valid date.") from exc


def iso_time(data: dict, key: str) -> time:
    try:
        return time.fromisoformat(str(data.get(key, "")))
    except ValueError as exc:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be a valid time.") from exc


def iso_datetime(data: dict, key: str, *, required: bool = True) -> datetime | None:
    raw = str(data.get(key, "")).strip()
    if not raw and not required:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be a valid date and time.") from exc

