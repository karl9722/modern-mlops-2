import os
import subprocess
import sys

from dagster import AssetExecutionContext, Definitions, asset


@asset
def house_price_training(context: AssetExecutionContext):
    context.log.info("Demarrage de l'entrainement immobilier")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["MLFLOW_TRACKING_URI"] = os.getenv(
    "MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")

    result = subprocess.run(
        [sys.executable, "scripts/train_model.py"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        context.log.info(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-4000:])

    return "Entrainement termine et enregistre dans MLflow"


defs = Definitions(assets=[house_price_training])


