from fastapi.testclient import TestClient

from mlops.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_gc_objects_collected_total" in response.text


def test_predict_invalid_input():
    response = client.post(
        "/predict",
        json={
            "surface": -10,
            "bedrooms": 2,
            "age": 5,
            "distance_center": 3.0,
        },
    )
    assert response.status_code == 422