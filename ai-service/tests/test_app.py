from fastapi.testclient import TestClient

from serviceops_ai.app import app


def test_predict_endpoint_and_model_info() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "title": "Production server down",
                "description": "The customer API returns errors and all workflows are blocked.",
            },
        )
        model_info = client.get("/model-info")

    assert response.status_code == 200
    assert set(response.json()) == {"category", "priority", "confidence", "modelVersion"}
    assert model_info.status_code == 200
    assert model_info.json()["trainingRows"] == 40


def test_predict_endpoint_returns_structured_validation_error() -> None:
    with TestClient(app) as client:
        response = client.post("/predict", json={"title": "bad", "description": "short"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_short"


def test_predict_endpoint_validates_trimmed_input() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "title": "     ",
                "description": "          ",
            },
        )

    assert response.status_code == 422
    fields = {entry["loc"][-1] for entry in response.json()["detail"]}
    assert fields == {"title", "description"}
