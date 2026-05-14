import os
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.models.database import init_db


BASE_DIR = Path(__file__).resolve().parent.parent


def _path_from_env(name, default):
    return Path(os.environ.get(name, default)).expanduser().resolve()


def _int_from_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def create_app():
    app = Flask(__name__)
    app_env = os.environ.get("APP_ENV", "development")
    data_dir = _path_from_env("APP_DATA_DIR", BASE_DIR / "data")
    upload_dir = _path_from_env("APP_UPLOAD_DIR", data_dir / "uploads")
    processed_dir = _path_from_env("APP_PROCESSED_DIR", data_dir / "processed")
    report_dir = _path_from_env("APP_REPORT_DIR", data_dir / "reports")
    db_path = _path_from_env("APP_DB_PATH", data_dir / "comparador_ipasgo.sqlite3")

    secret_key = os.environ.get("SECRET_KEY", "comparador-ipasgo-local")
    if app_env == "production" and secret_key == "comparador-ipasgo-local":
        raise RuntimeError("SECRET_KEY precisa ser configurada em produção.")

    app.config["SECRET_KEY"] = secret_key
    app.config["BASE_DIR"] = BASE_DIR
    app.config["DATA_DIR"] = data_dir
    app.config["UPLOAD_DIR"] = upload_dir
    app.config["PROCESSED_DIR"] = processed_dir
    app.config["REPORT_DIR"] = report_dir
    app.config["DB_PATH"] = db_path
    app.config["MAX_CONTENT_LENGTH"] = _int_from_env("MAX_UPLOAD_MB", 80) * 1024 * 1024
    app.config["PREFERRED_URL_SCHEME"] = os.environ.get("PREFERRED_URL_SCHEME", "http")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = app.config["PREFERRED_URL_SCHEME"] == "https"

    if os.environ.get("TRUST_PROXY", "0") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    for folder in (upload_dir, processed_dir, report_dir):
        folder.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    from app.routes.main_routes import main_bp
    from app.routes.import_routes import import_bp
    from app.routes.comparison_routes import comparison_bp
    from app.routes.report_routes import report_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(comparison_bp)
    app.register_blueprint(report_bp)
    return app
