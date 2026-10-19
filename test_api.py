from pathlib import Path
from fastapi.testclient import TestClient
from api.app import app


def test_health_and_single_driver_scoring():
    client = TestClient(app)
    health = client.get('/health')
    assert health.status_code == 200
    payload = {
        "driver_id": "D_TEST_001",
        "zone": "central",
        "daypart": "late_night",
        "avg_online_hours_4w": 18.5,
        "avg_trips_4w": 42.0,
        "cancellation_rate": 0.08,
        "demand_index": 0.92,
        "acceptance_rate": 0.86,
        "tenure_days": 420,
        "is_active_pre": 1,
    }
    response = client.post('/score', json=payload)
    if Path('artifacts/uplift_model.joblib').exists():
        assert response.status_code == 200
        body = response.json()
        assert body['driver_id'] == 'D_TEST_001'
        assert 'predicted_incremental_trips' in body
        assert body['data_classification'].startswith('synthetic_portfolio_model')
    else:
        assert response.status_code == 503


def test_batch_scoring_and_category_validation():
    client = TestClient(app)
    payload = {
        "driver_id": "D_TEST_002",
        "zone": "central",
        "daypart": "morning",
        "avg_online_hours_4w": 20.0,
        "avg_trips_4w": 40.0,
        "cancellation_rate": 0.05,
        "demand_index": 1.05,
        "acceptance_rate": 0.9,
        "tenure_days": 365,
        "is_active_pre": 1,
    }
    response = client.post('/score/batch', json={"drivers": [payload, payload]})
    if Path('artifacts/uplift_model.joblib').exists():
        assert response.status_code == 200
        assert response.json()['count'] == 2
        assert len(response.json()['scores']) == 2
    else:
        assert response.status_code == 503
    bad_payload = {**payload, "zone": "unknown-zone"}
    bad_response = client.post('/score', json=bad_payload)
    assert bad_response.status_code == 422
