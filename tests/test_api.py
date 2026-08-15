from fastapi.testclient import TestClient

from backend.api.app import app
from backend.infrastructure.config.settings import load_settings
from backend.use_cases.use_case_1_autocomplete.service import AutocompleteService

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "provider" in data


def test_autocomplete_endpoint_validation_error():
    settings = load_settings()
    settings.provider = "mock"
    app.state.autocomplete_service = AutocompleteService(settings)

    response = client.post("/api/v1/autocomplete", json={"text": "hi"})
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "too short" in data["message"]


def test_autocomplete_endpoint_success_with_mock():
    settings = load_settings()
    settings.provider = "mock"
    app.state.autocomplete_service = AutocompleteService(settings)

    response = client.post(
        "/api/v1/autocomplete",
        json={"text": "Artificial Intelligence is"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "completion" in data
    assert "execution_time_sec" in data
