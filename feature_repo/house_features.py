from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float64, Int64

house = Entity(
    name="house_id",
    join_keys=["house_id"],
)

house_source = FileSource(
    name="house_source",
    path="data/houses.parquet",
    timestamp_field="event_timestamp",
)

house_features = FeatureView(
    name="house_features",
    entities=[house],
    ttl=timedelta(days=365),
    schema=[
        Field(name="surface", dtype=Int64),
        Field(name="bedrooms", dtype=Int64),
        Field(name="age", dtype=Int64),
        Field(name="distance_center", dtype=Float64),
    ],
    source=house_source,
    online=True,
)
