from flask_login import current_user

from app.extensions import db
from app.models import ActivityLog


def record_activity(action: str, entity_type: str, entity_id: object = "", details: str = "") -> None:
    user_id = current_user.id if getattr(current_user, "is_authenticated", False) else None
    db.session.add(
        ActivityLog(
            user_id=user_id,
            action=action[:120],
            entity_type=entity_type[:80],
            entity_id=str(entity_id)[:80],
            details=details[:300],
        )
    )

