import pytest
from fastapi.testclient import TestClient

from db import Base, engine
from main import app

PASSWORD = "open sesame"
ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def test_open_when_no_password_is_set(client, monkeypatch):
    monkeypatch.delenv("ACCESS_PASSWORD", raising=False)
    assert client.get("/api/stats").status_code == 200
    assert client.get("/api/access").json() == {"required": False, "granted": True}


def test_password_required_on_api_routes(client, monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", PASSWORD)
    for method, path in (
        ("GET", "/api/stats"), ("GET", "/api/associates"), ("GET", "/api/credentials"), ("GET", "/api/alerts"),
        ("GET", "/api/filters"), ("GET", "/api/jobs/daily"), ("GET", "/api/evidence/1.pdf"),
        ("POST", "/api/verify/all"), ("POST", "/api/jobs/daily/run"), ("POST", "/api/alerts/run"),
    ):
        response = client.request(method, path)
        assert response.status_code == 401, path
        assert response.json() == {"detail": "Access password required"}
    assert client.get("/api/stats", headers={"X-Access-Password": "wrong"}).status_code == 401
    assert client.get("/api/stats", params={"access": "wrong"}).status_code == 401


def test_password_accepted_by_header_or_query(client, monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", PASSWORD)
    assert client.get("/api/stats", headers={"X-Access-Password": PASSWORD}).status_code == 200
    assert client.get("/api/stats", params={"access": PASSWORD}).status_code == 200


def test_health_and_access_status_stay_open(client, monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", PASSWORD)
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/access").json() == {"required": True, "granted": False}
    assert client.get("/api/access", headers={"X-Access-Password": "wrong"}).json()["granted"] is False
    assert client.get("/api/access", headers={"X-Access-Password": PASSWORD}).json() == {
        "required": True, "granted": True,
    }


def test_browser_can_read_the_401_and_preflight_passes(client, monkeypatch):
    monkeypatch.setenv("ACCESS_PASSWORD", PASSWORD)
    refused = client.get("/api/stats", headers=ORIGIN)
    assert refused.status_code == 401
    assert refused.headers["access-control-allow-origin"] == "http://localhost:3000"

    preflight = client.options("/api/stats", headers={
        **ORIGIN, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "x-access-password",
    })
    assert preflight.status_code == 200
    assert "x-access-password" in preflight.headers["access-control-allow-headers"].lower()
