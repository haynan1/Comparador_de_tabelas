import os
import tempfile

import pytest

from app import create_app


@pytest.fixture(scope="module")
def test_app():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        saved = {k: os.environ.get(k) for k in ("APP_DATA_DIR", "APP_ENV", "LOGIN_PASSWORD")}
        os.environ["APP_DATA_DIR"] = tmp
        os.environ["APP_ENV"] = "development"
        os.environ.pop("LOGIN_PASSWORD", None)

        application = create_app()
        application.config["TESTING"] = True
        application.config["WTF_CSRF_ENABLED"] = False

        yield application

        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture(scope="module")
def client(test_app):
    return test_app.test_client()


class TestPublicRoutes:
    def test_landing_page(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_healthz(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

    def test_dashboard(self, client):
        response = client.get("/comparacoes")
        assert response.status_code == 200

    def test_nova_comparacao(self, client):
        response = client.get("/comparacoes/nova")
        assert response.status_code == 200


class TestAuthGate:
    def test_no_password_set_allows_all(self, client):
        response = client.get("/comparacoes")
        assert response.status_code == 200

    def test_login_page_accessible(self, client):
        # When LOGIN_PASSWORD is not set, /login redirects to dashboard
        response = client.get("/login")
        assert response.status_code in (200, 302)

    def test_login_with_password_set(self, test_app):
        test_app.config["LOGIN_PASSWORD"] = "testpass123"
        with test_app.test_client() as c:
            response = c.get("/comparacoes")
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]

            response = c.post("/login", data={"password": "testpass123"})
            assert response.status_code == 302

            response = c.get("/comparacoes")
            assert response.status_code == 200
        test_app.config["LOGIN_PASSWORD"] = ""

    def test_wrong_password_rejected(self, test_app):
        test_app.config["LOGIN_PASSWORD"] = "testpass123"
        with test_app.test_client() as c:
            response = c.post("/login", data={"password": "wrongpass"}, follow_redirects=True)
            assert b"Senha incorreta" in response.data
        test_app.config["LOGIN_PASSWORD"] = ""


class TestDownloadRoute:
    def test_nonexistent_comparison_redirects(self, client):
        response = client.get("/relatorios/99999/excel")
        assert response.status_code == 302

    def test_invalid_kind_redirects(self, client):
        response = client.get("/relatorios/1/invalid")
        assert response.status_code in (302, 404)
