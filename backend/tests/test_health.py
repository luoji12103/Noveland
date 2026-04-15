from fastapi.testclient import TestClient
from noveland.services.api.app import create_app


def test_health_returns_fixed_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api", "status": "ok", "version": "0.1.0"}
