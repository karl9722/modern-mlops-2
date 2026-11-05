"""Regression checks beyond the examples in the assignment."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from mlflow.exceptions import MlflowException

from mlops import api, registry, settings
from mlops.evaluation import behaviour_checks, promotion_gate
from mlops.monitoring import check_quality
from mlops.train import time_split


@pytest.mark.parametrize("metric", ["r2", "rmse"])
def test_gate_rejects_nonfinite_metrics(metric):
    metrics = {"r2": 0.9, "rmse": 10.0, metric: float("nan")}
    assert not promotion_gate(metrics, None, [], 0.7).passed


def test_behaviour_rejects_nonfinite_modified_prediction():
    class Broken:
        def predict(self, frame):
            return [100.0 if frame.GrLivArea.iloc[0] == 1500 else float("nan")]

    assert behaviour_checks(Broken())


def test_temporal_split_never_shares_a_month():
    frame = pd.DataFrame(
        {
            settings.TIMESTAMP: pd.to_datetime(
                ["2007-01-01", "2008-01-01", "2009-01-01", "2009-01-01", "2010-01-01"]
            )
        }
    )
    train, test = time_split(frame, 0.4)
    assert train[settings.TIMESTAMP].max() < test[settings.TIMESTAMP].min()


def test_missing_alias_does_not_hide_a_server_failure():
    class Down:
        def get_model_version_by_alias(self, *_):
            raise MlflowException("unavailable", error_code="INTERNAL_ERROR")

    with pytest.raises(MlflowException):
        registry._alias_version(Down(), "champion")


def test_promote_refuses_rejected_version(monkeypatch):
    class Client:
        def get_model_version(self, *_):
            return SimpleNamespace(tags={"gate_passed": "false", "gate_reasons": "worse"})

        def set_registered_model_alias(self, *_):
            pytest.fail("Rejected version must never acquire a serving alias")

    monkeypatch.setattr(registry, "_client", Client)
    with pytest.raises(SystemExit, match="did not pass"):
        registry.promote("2")


def test_model_holder_recovers_and_throttles_retries():
    calls = []

    def loader():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("MLflow still starting")
        return api.LoadedModel(object(), "3")

    holder = api.ModelHolder(loader, retry_seconds=30)
    assert holder.get() is None
    assert holder.get() is None
    assert len(calls) == 1
    holder._last_attempt -= 31
    assert holder.get().version == "3"


def test_insufficient_feedback_is_skipped_not_passed():
    class Store:
        def labelled_predictions(self, *_):
            return pd.DataFrame()

    result = check_quality(Store(), "1", 100)
    assert result.passed is None
    assert result.value is None
    assert "skipped" in result.details


def test_quality_shift_fails():
    class Store:
        def labelled_predictions(self, *_):
            return pd.DataFrame(
                {"predicted_price": np.full(30, 200000), "actual_price": np.full(30, 320000)}
            )

    result = check_quality(Store(), "1", 30000)
    assert result.passed is False
    assert result.value > result.threshold
