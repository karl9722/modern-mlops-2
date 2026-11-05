import os

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from pyspark.sql import SparkSession
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# Connexion au serveur MLflow
mlflow.set_tracking_uri(
    os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
)
mlflow.set_experiment("house-price-prediction")

# Donnees reproductibles pour notre premier pipeline
rng = np.random.default_rng(42)
n = 500

data = pd.DataFrame({
    "surface": rng.integers(30, 250, n),
    "bedrooms": rng.integers(1, 6, n),
    "age": rng.integers(0, 50, n),
    "distance_center": rng.uniform(1, 30, n),
})

data["price"] = (
    data["surface"] * 3000
    + data["bedrooms"] * 15000
    - data["age"] * 1000
    - data["distance_center"] * 2500
    + rng.normal(0, 20000, n)
)

# Preparation avec PySpark
spark = (
    SparkSession.builder
    .master("local[2]")
    .appName("modern-mlops-house-prices")
    .getOrCreate()
)

spark_df = spark.createDataFrame(data)
spark_df = spark_df.dropna()
prepared = spark_df.toPandas()
spark.stop()

# Entrainement
features = ["surface", "bedrooms", "age", "distance_center"]
X = prepared[features]
y = prepared["price"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

with mlflow.start_run(run_name="random-forest-baseline"):
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=2,
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    mlflow.log_param("model", "RandomForestRegressor")
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("training_rows", len(X_train))
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2", r2)

    mlflow.sklearn.log_model(
        model,
        name="house_price_model",
        skops_trusted_types=["sklearn.tree._tree.Tree"],
        input_example=X_train.head(3),
    )

    print(f"MAE : {mae:.2f}")
    print(f"R2  : {r2:.4f}")
    print("Modele enregistre dans MLflow !")

