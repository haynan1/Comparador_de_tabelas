from urllib.parse import urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.auth import check_password


auth_bp = Blueprint("auth", __name__)


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return not parsed.netloc and not parsed.scheme and url.startswith("/")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if not current_app.config.get("LOGIN_PASSWORD"):
        return redirect(url_for("main.dashboard"))
    if session.get("authenticated"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        if check_password(request.form.get("password", "")):
            session["authenticated"] = True
            session.permanent = True
            next_url = request.form.get("next", "")
            if next_url and _is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for("main.dashboard"))
        flash("Senha incorreta.", "error")
    return render_template("login.html", next=request.args.get("next", ""))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
