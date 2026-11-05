from datetime import datetime, timedelta, timezone
from feast import FeatureStore

store = FeatureStore(repo_path="feature_repo")

store.materialize(
    start_date=datetime.now(timezone.utc) - timedelta(days=1),
    end_date=datetime.now(timezone.utc) + timedelta(minutes=5),
)

result = store.get_online_features(
    features=[
        "house_features:surface",
        "house_features:bedrooms",
        "house_features:age",
        "house_features:distance_center",
    ],
    entity_rows=[{"house_id": 1}],
).to_dict()

print("Features maison 1 :", result)
