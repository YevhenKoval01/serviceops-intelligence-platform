from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from serviceops_ai.app import app

JWT_SECRET = "local-development-signing-key-change-me-2026"


def authorization(role: str = "OPERATOR") -> dict[str, str]:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "serviceops-local",
            "aud": ["serviceops-api"],
            "sub": role.lower(),
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "roles": [role],
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_predict_endpoint_and_model_info() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            headers=authorization(),
            json={
                "title": "Production server down",
                "description": "The customer API returns errors and all workflows are blocked.",
            },
        )
        model_info = client.get("/model-info", headers=authorization("VIEWER"))

    assert response.status_code == 200
    assert set(response.json()) == {"category", "priority", "confidence", "modelVersion"}
    assert model_info.status_code == 200
    assert model_info.json()["trainingRows"] == 40


def test_predict_endpoint_returns_structured_validation_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            headers=authorization(),
            json={"title": "bad", "description": "short"},
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_short"


def test_predict_endpoint_validates_trimmed_input() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            headers=authorization(),
            json={
                "title": "     ",
                "description": "          ",
            },
        )

    assert response.status_code == 422
    fields = {entry["loc"][-1] for entry in response.json()["detail"]}
    assert fields == {"title", "description"}


def test_prediction_requires_operator_role() -> None:
    request = {
        "title": "Production server down",
        "description": "The customer API returns errors and all workflows are blocked.",
    }
    with TestClient(app) as client:
        anonymous = client.post("/predict", json=request)
        viewer = client.post("/predict", headers=authorization("VIEWER"), json=request)

    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"] == "Bearer"
    assert viewer.status_code == 403


def test_rejects_token_with_wrong_signature() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "serviceops-local",
            "aud": ["serviceops-api"],
            "sub": "operator",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "roles": ["OPERATOR"],
        },
        "different-signing-key-with-at-least-32-bytes",
        algorithm="HS256",
    )
    with TestClient(app) as client:
        response = client.get("/model-info", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
