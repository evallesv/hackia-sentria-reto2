import base64

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def protected_client(tmp_path):
    settings = Settings(
        _env_file=None,
        ai_mode="mock",
        upload_dir=str(tmp_path / "uploads"),
        demo_auth_enabled=True,
        demo_username="jurado",
        demo_password="test-access-password",
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("GET", "/static/app.js"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("GET", "/api/demo/A"),
        ("POST", "/api/claims"),
        ("POST", "/api/claims/admin/purge?dry_run=false"),
        ("POST", "/api/demo/B/audit"),
        ("GET", "/api/claims/private/documents/private-document"),
    ],
)
def test_unauthenticated_access_is_blocked(protected_client, method, path):
    response = protected_client.request(method, path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith('Basic realm="Sentria"')


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer wrong",
        "Basic invalid-base64!",
        "Basic " + base64.b64encode(b"missing-separator").decode(),
        "Basic " + base64.b64encode(b"wrong:test-access-password").decode(),
        "Basic " + base64.b64encode(b"jurado:wrong").decode(),
    ],
)
def test_invalid_credentials_are_rejected(protected_client, authorization):
    response = protected_client.get("/", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert "test-access-password" not in response.text


def test_valid_credentials_allow_document_flow(protected_client):
    auth = ("jurado", "test-access-password")
    assert protected_client.get("/", auth=auth).status_code == 200
    response = protected_client.post("/api/claims", json={"claim_id": "CLM-JUDGE"}, auth=auth)
    assert response.status_code == 201
    assert protected_client.get("/api/claims/CLM-JUDGE", auth=auth).status_code == 200
    assert protected_client.get("/api/claims/CLM-JUDGE").status_code == 401


def test_healthcheck_remains_available(protected_client):
    assert protected_client.get("/healthz").status_code == 200


def test_enabled_authentication_requires_a_password(tmp_path):
    settings = Settings(
        _env_file=None,
        ai_mode="mock",
        upload_dir=str(tmp_path / "uploads"),
        demo_auth_enabled=True,
        demo_password="",
    )
    with pytest.raises(ValueError, match="DEMO_PASSWORD"):
        create_app(settings)
