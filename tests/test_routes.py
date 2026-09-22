import os
import re
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


class TestComparisonReportFlow:
    """Fluxo completo: executar comparação -> baixar PDF com todos os registros."""

    def _write_inputs(self, upload_dir, n):
        from test_pdf_report import _cpf

        pref = upload_dir / "pref_fluxo.csv"
        ipa = upload_dir / "ipa_fluxo.csv"
        cpfs = [_cpf(5000 + i) for i in range(n)]
        pref.write_text("CPF;Nome;Valor\n" + "".join(f"{c};SERVIDOR {i};100,00\n" for i, c in enumerate(cpfs)), encoding="utf-8")
        ipa.write_text("CPF;Nome;Valor\n" + "".join(f"{c};SERVIDOR {i};90,00\n" for i, c in enumerate(cpfs)), encoding="utf-8")
        return pref, ipa, cpfs

    def _form(self, pref, ipa):
        return {
            "prefeitura_path": str(pref), "ipasgo_path": str(ipa),
            "prefeitura_cpf": "CPF", "prefeitura_nome": "Nome", "prefeitura_valor": "Valor",
            "ipasgo_cpf": "CPF", "ipasgo_nome": "Nome", "ipasgo_valor": "Valor",
            "tolerancia": "0,01",
        }

    def test_pdf_download_contains_all_rows(self, test_app, client):
        from test_pdf_report import _pdf_text

        upload_dir = test_app.config["UPLOAD_DIR"]
        upload_dir.mkdir(parents=True, exist_ok=True)
        pref, ipa, cpfs = self._write_inputs(upload_dir, 75)  # > antigo limite de 40

        response = client.post("/comparacoes/executar", data=self._form(pref, ipa))
        assert response.status_code == 302
        location = response.headers["Location"]
        match = re.search(r"/comparacoes/(\d+)$", location)
        assert match, location
        comparison_id = int(match.group(1))

        pdf = client.get(f"/relatorios/{comparison_id}/pdf")
        assert pdf.status_code == 200
        assert pdf.data.startswith(b"%PDF")

        pdf_path = upload_dir / "baixado.pdf"
        pdf_path.write_bytes(pdf.data)
        text = _pdf_text(pdf_path)
        assert "Tabela principal de divergências" in text
        for cpf in cpfs:
            assert f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" in text

    def test_rejects_paths_outside_upload_dir(self, test_app, client, tmp_path):
        pref, ipa, _ = self._write_inputs(tmp_path, 1)
        response = client.post("/comparacoes/executar", data=self._form(pref, ipa))
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/comparacoes/nova")
