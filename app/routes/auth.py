from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import limiter
from app.models import User


bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> bool:
    if not target:
        return False
    host = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    return candidate.scheme in {"http", "https"} and host.netloc == candidate.netloc


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user, remember=False)
            next_url = request.args.get("next")
            return redirect(next_url if _safe_next(next_url) else url_for("dashboard.index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

