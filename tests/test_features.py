"""Verify the actual Feast join cannot read a future feature value."""

from datetime import timedelta

import pandas as pd
import pytest
from feast import FeatureStore, FeatureView, Field, FileSource
from feast.types import Float64

from mlops import features, settings


@pytest.fixture
def historical_store(tmp_path, monkeypatch):
    source_path = tmp_path / "source.parquet"
    source = pd.DataFrame(
        {
            settings.ENTITY_KEY: [1, 1],
            settings.TIMESTAMP: pd.to_datetime(["2008-01-01", "2010-01-01"], utc=True),
            **{name: [1.0, 99.0] for name in settings.FEATURES},
        }
    )
    source.to_parquet(source_path, index=False)
    (tmp_path / "feature_store.yaml").write_text(
        "project: test_point_in_time\nprovider: local\nregistry: registry.db\n"
        "online_store:\n  type: sqlite\n  path: online.db\n"
        "offline_store:\n  type: file\nentity_key_serialization_version: 3\n"
    )
    store = FeatureStore(repo_path=str(tmp_path))
    view = FeatureView(
        name=features.housing_features.name,
        entities=[features.house],
        ttl=timedelta(days=3650),
        online=False,
        schema=[Field(name=name, dtype=Float64) for name in settings.FEATURES],
        source=FileSource(
            name="test_source", path=str(source_path), timestamp_field=settings.TIMESTAMP
        ),
    )
    store.apply([features.house, view])
    processed = tmp_path / "labels.parquet"
    monkeypatch.setattr(settings, "PROCESSED_PATH", processed)
    monkeypatch.setattr(features, "get_store", lambda: store)
    return processed


def test_feast_uses_only_values_known_at_sale_time(historical_store):
    pd.DataFrame(
        {
            settings.ENTITY_KEY: [1],
            settings.TIMESTAMP: pd.to_datetime(["2009-01-01"], utc=True),
            settings.TARGET: [200000.0],
        }
    ).to_parquet(historical_store, index=False)
    frame = features.get_training_frame()
    assert len(frame) == 1
    assert frame[settings.FEATURES].iloc[0].tolist() == [1.0] * len(settings.FEATURES)


def test_feast_refuses_sale_before_any_features_existed(historical_store):
    pd.DataFrame(
        {
            settings.ENTITY_KEY: [1],
            settings.TIMESTAMP: pd.to_datetime(["2007-01-01"], utc=True),
            settings.TARGET: [200000.0],
        }
    ).to_parquet(historical_store, index=False)
    with pytest.raises(ValueError, match="without features"):
        features.get_training_frame()
