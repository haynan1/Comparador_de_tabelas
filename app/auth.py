import secrets
from functools import wraps

from flask import current_app, redirect, session, url_for


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get("LOGIN_PASSWORD"):
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def check_password(candidate: str) -> bool:
    stored = current_app.config.get("LOGIN_PASSWORD", "")
    return bool(stored) and secrets.compare_digest(candidate, stored)
