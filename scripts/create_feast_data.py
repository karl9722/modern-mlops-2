from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 500

df = pd.DataFrame({
    "house_id": np.arange(1, n + 1, dtype="int64"),
    "surface": rng.integers(30, 250, n).astype("int64"),
    "bedrooms": rng.integers(1, 6, n).astype("int64"),
    "age": rng.integers(0, 50, n).astype("int64"),
    "distance_center": rng.uniform(1, 30, n),
    "event_timestamp": pd.Timestamp.now(tz="UTC"),
})

path = Path("feature_repo/data/houses.parquet")
path.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(path, index=False)

print(f"Donnees creees : {len(df)} maisons")
