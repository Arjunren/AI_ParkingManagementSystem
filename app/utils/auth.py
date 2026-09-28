from functools import wraps

from flask import abort, jsonify, request
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Administrator access required."}), 403
            abort(403)
        return view(*args, **kwargs)

    return wrapped

