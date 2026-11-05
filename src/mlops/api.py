import logging
import os

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="Modern MLOps - House Price API")


from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

Instrumentator().add(metrics.default()).instrument(app)

@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
mlflow.set_tracking_uri(MLFLOW_URI)

model = None

class House(BaseModel):
    surface: int = Field(gt=0)
    bedrooms: int = Field(ge=0)
    age: int = Field(ge=0)
    distance_center: float = Field(ge=0)

@app.on_event("startup")
def load_model():
    global model
    client = mlflow.MlflowClient()
    runs = client.search_runs(
        experiment_ids=["1"],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"],
        max_results=10,
    )
    for run in runs:
        try:
            model = mlflow.pyfunc.load_model(f"runs:/{run.info.run_id}/house_price_model")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Impossible de charger le mod?le MLflow : %s", exc)
            continue
    raise RuntimeError("Aucun modele MLflow utilisable trouve")

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/predict")
def predict(house: House):
    if model is None:
        raise HTTPException(status_code=503, detail="Modele indisponible")

    data = pd.DataFrame([house.model_dump()])
    prediction = float(model.predict(data)[0])
    return {"predicted_price": round(prediction, 2)}


