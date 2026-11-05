"""PostgreSQL integration tests; explicitly enabled with TEST_DATABASE_URL."""

import os
import uuid

import psycopg
import pytest

from mlops.db import PredictionStore


@pytest.mark.integration
def test_postgres_prediction_feedback_and_skipped_monitoring():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated test database")
    store = PredictionStore(url)
    prediction_id = uuid.uuid4()
    try:
        assert not store.add_feedback(uuid.uuid4(), 240000)
        store.log_prediction(prediction_id, "integration-test", {"OverallQual": 7}, 250000)
        assert store.add_feedback(prediction_id, 240000)
        assert store.add_feedback(prediction_id, 245000)
        labelled = store.labelled_predictions(1, "integration-test")
        row = labelled[labelled.prediction_id == prediction_id].iloc[0]
        assert row.actual_price == 245000
        store.record_check(
            "integration-test", "integration-test", None, 0.5, None, {"skipped": "not enough data"}
        )
        with psycopg.connect(url) as conn:
            assert conn.execute(
                "SELECT passed FROM monitoring_results WHERE check_name = %s"
                " ORDER BY id DESC LIMIT 1",
                ("integration-test",),
            ).fetchone() == (None,)
    finally:
        store.close()
        with psycopg.connect(url) as conn:
            conn.execute("DELETE FROM feedback WHERE prediction_id = %s", (prediction_id,))
            conn.execute("DELETE FROM predictions WHERE prediction_id = %s", (prediction_id,))
            conn.execute(
                "DELETE FROM monitoring_results WHERE check_name = %s", ("integration-test",)
            )
