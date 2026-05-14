from app import create_app
import pytest


def test_app_uses_configured_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    app = create_app()

    assert app.config["DATA_DIR"] == tmp_path.resolve()
    assert app.config["DB_PATH"] == tmp_path.resolve() / "comparador_ipasgo.sqlite3"
    assert app.config["DB_PATH"].exists()


def test_healthz_route(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    app = create_app()

    response = app.test_client().get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_home_renders_link_hub(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    app = create_app()

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"link-hub-shell" in response.data


def test_production_requires_secret_key(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()
