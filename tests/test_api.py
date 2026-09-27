from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app, load_case


def client(**kwargs):
    return TestClient(create_app(Settings(_env_file=None, ai_mode="mock", **kwargs)))


def test_guided_home_and_demo_api():
    with client() as c:
        page = c.get("/")
        assert page.status_code == 200
        assert "Modo simulación" in page.text
        assert "Prueba guiada" in page.text
        assert "default-src 'self'" in page.headers["Content-Security-Policy"]
        assert c.get("/healthz").json()["mode"] == "mock"
        result = c.post("/api/demo/C/audit").json()
        assert result["flagged_difference"] == "250.00"
        assert c.post("/api/demo/C/audit").json() == result
        assert c.get("/api/demo/UNKNOWN").status_code == 404


def test_public_demo_rejects_custom_data():
    with client() as c:
        response = c.post("/api/audits", json=load_case("A").model_dump(mode="json"))
        assert response.status_code == 403


def test_local_custom_input_validation():
    with client(enable_custom_input=True) as c:
        assert c.post("/api/audits", json={}).status_code == 422
        response = c.post("/api/audits", json=load_case("B").model_dump(mode="json"))
        assert response.status_code == 200
        assert response.json()["flagged_difference"] == "80.00"


def test_request_limit():
    with client(max_request_bytes=1024) as c:
        assert c.post("/api/audits", content=b"x" * 1025).status_code == 413
        assert c.post("/api/audits", content=iter([b"x" * 700, b"x" * 700])).status_code == 413
