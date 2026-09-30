import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from faultlab.api import app
from faultlab.db import Base, get_db


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def create_experiment(client: TestClient) -> str:
    service_id = client.post("/api/services", json={"name": "gateway"}).json()["id"]
    response = client.post("/api/experiments", json={
        "service_id": service_id, "requests_per_second": 10, "concurrency": 5,
        "baseline_seconds": 1, "fault_seconds": 1, "recovery_seconds": 1,
        "fault": {"type": "latency", "latency_ms": 300}})
    assert response.status_code == 201
    return response.json()["id"]


def test_service_registration_is_allowlisted(client: TestClient):
    assert client.post("/api/services", json={"name": "arbitrary"}).status_code == 422
    assert client.post("/api/services", json={"name": "gateway"}).status_code == 201
    assert client.post("/api/services", json={"name": "gateway"}).status_code == 409
    assert len(client.get("/api/services").json()) == 1


def test_experiment_start_cancel_and_report_gate(client: TestClient):
    experiment_id = create_experiment(client)
    assert client.get(f"/api/experiments/{experiment_id}/report").status_code == 409
    assert client.post(f"/api/experiments/{experiment_id}/start").status_code == 200
    assert client.post(f"/api/experiments/{experiment_id}/start").status_code == 409
    assert client.post(f"/api/experiments/{experiment_id}/cancel").status_code == 200
    assert client.get(f"/api/experiments/{experiment_id}/metrics").json() == []
    assert client.post(f"/api/experiments/{experiment_id}/cancel").status_code == 409


def test_invalid_inputs(client: TestClient):
    assert client.post("/api/experiments", json={"service_id": "unknown"}).status_code == 422
    service_id = client.post("/api/services", json={"name": "gateway"}).json()["id"]
    base = {"service_id": service_id, "requests_per_second": 10, "concurrency": 1,
            "baseline_seconds": 1, "fault_seconds": 1, "recovery_seconds": 1,
            "fault": {"type": "latency", "latency_ms": 100}}
    for change in ({"requests_per_second": 0}, {"requests_per_second": 51},
                   {"baseline_seconds": -1}, {"fault": {"type": "unknown"}}):
        assert client.post("/api/experiments", json={**base, **change}).status_code == 422
    assert client.post("/api/experiments", json={**base, "service_id": "unknown"}).status_code == 404


def test_unknown_experiment(client: TestClient):
    assert client.get("/api/experiments/missing").status_code == 404
    assert client.get("/api/experiments/missing/metrics").status_code == 404
