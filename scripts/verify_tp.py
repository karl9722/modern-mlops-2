"""Exercise the TP against an isolated local development stack.

Run with `uv run --all-groups --env-file .env python scripts/verify_tp.py`.
This explicitly promotes test models, replays labelled sales, and tests rollback.
It does not publish images or change a remote repository.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import mlflow
import pandas as pd
from mlflow import MlflowClient

from mlops import settings
from mlops.db import PredictionStore
from mlops.monitoring import champion_info, check_drift, check_quality
from mlops.orchestration import defs
from mlops.registry import promote, rollback
from mlops.train import train_candidate


def main() -> None:
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {}
    env = os.environ.copy()
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    base = "http://127.0.0.1:18001"
    key = next(iter(settings.api_keys()))
    headers = {"X-API-Key": key}
    process = None

    def start_api(expected: str):
        nonlocal process
        if process is not None:
            process.terminate()
            process.wait(timeout=20)
        log = (settings.REPORTS_DIR / "verification-api.log").open("ab")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mlops.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                "18001",
                "--no-access-log",
            ],
            cwd=settings.ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        log.close()
        for _ in range(90):
            if process.poll() is not None:
                raise RuntimeError("Verification API failed; see verification-api.log")
            try:
                r = httpx.get(base + "/ready", timeout=2)
                if r.status_code == 200:
                    assert r.json()["model_version"] == expected
                    return
            except httpx.TransportError:
                pass
            time.sleep(1)
        raise RuntimeError("API readiness timed out")

    store = PredictionStore(settings.require_database_url())
    try:
        result = defs.resolve_job_def("training_job").execute_in_process()
        assert result.success
        client = MlflowClient(tracking_uri=settings.MLFLOW_TRACKING_URI)
        candidate = client.get_model_version_by_alias(settings.MODEL_NAME, "challenger")
        assert candidate.tags["gate_passed"] == "true"
        baseline = promote(str(candidate.version))
        start_api(baseline)
        evidence["training_job"] = {"success": True, "baseline_version": baseline}

        subprocess.run(
            [sys.executable, "scripts/smoke_test.py", "--api-key", key, "--base-url", base],
            cwd=settings.ROOT,
            env=env,
            check=True,
        )
        evidence["smoke"] = "passed"
        subprocess.run(
            [
                sys.executable,
                "scripts/replay_holdout.py",
                "--api-key",
                key,
                "--base-url",
                base,
                "--rows",
                "200",
            ],
            cwd=settings.ROOT,
            env=env,
            check=True,
        )
        version, holdout = champion_info()
        quality = check_quality(store, version, holdout)
        drift = check_drift(store)
        assert quality.passed is True, quality
        assert drift.passed is True, drift
        for check in (quality, drift):
            store.record_check(
                check.name, version, check.value, check.threshold, check.passed, check.details
            )
        evidence["monitoring"] = {
            "rmse": quality.value,
            "limit": quality.threshold,
            "drift_share": drift.value,
        }

        monitoring = defs.resolve_job_def("monitoring_job").execute_in_process()
        assert monitoring.success
        evidence["monitoring_job"] = "passed"

        rejected = train_candidate(alpha=1000)
        assert not rejected.decision.passed
        try:
            promote(rejected.model_version)
        except SystemExit:
            pass
        else:
            raise AssertionError("A rejected model was promoted")
        assert (
            str(client.get_model_version_by_alias(settings.MODEL_NAME, "champion").version)
            == baseline
        )
        evidence["gate_rejection"] = {
            "version": rejected.model_version,
            "reasons": rejected.decision.reasons,
        }

        accepted = train_candidate(alpha=1)
        assert accepted.decision.passed
        promoted = promote(accepted.model_version)
        start_api(promoted)
        assert rollback(None) == baseline
        start_api(baseline)
        evidence["promotion_rollback"] = {"promoted": promoted, "restored": baseline}

        # Use a distinct registered version to keep deliberately shifted feedback out of
        # the baseline champion's accuracy window once the exercise is over.
        promote(promoted)
        start_api(promoted)
        subprocess.run(
            [
                sys.executable,
                "scripts/replay_holdout.py",
                "--api-key",
                key,
                "--base-url",
                base,
                "--rows",
                "200",
                "--price-shift",
                "1.6",
            ],
            cwd=settings.ROOT,
            env=env,
            check=True,
        )
        version, holdout = champion_info()
        shifted = check_quality(store, version, holdout)
        assert shifted.passed is False
        store.record_check(
            shifted.name, version, shifted.value, shifted.threshold, shifted.passed, shifted.details
        )
        failed = defs.resolve_job_def("monitoring_job").execute_in_process(raise_on_error=False)
        assert not failed.success
        rollback(baseline)
        start_api(baseline)
        evidence["accuracy_alert"] = {
            "rmse": shifted.value,
            "limit": shifted.threshold,
            "dagster_run_failed": True,
        }

        # Exercise the blocking Spark asset and restore the exact original raw bytes.
        raw = settings.RAW_PATH.read_bytes()
        try:
            frame = pd.read_csv(settings.RAW_PATH)
            frame.loc[:3, "OverallQual"] = 42
            frame.to_csv(settings.RAW_PATH, index=False)
            bad = defs.resolve_job_def("training_job").execute_in_process(raise_on_error=False)
            assert not bad.success
            report = json.loads(settings.VALIDATION_REPORT_PATH.read_text())
            assert not report["passed"]
            assert any("OverallQual" in reason for reason in report["failures"])
            evidence["bad_data"] = report["failures"]
        finally:
            settings.RAW_PATH.write_bytes(raw)
            from mlops.data import prepare_data

            prepare_data()

        # Keep proof of request/version traceability in the evidence, without API keys.
        with httpx.Client(base_url=base, headers=headers) as http:
            row = pd.read_parquet(settings.PROCESSED_PATH).iloc[-1]
            payload = {name: float(row[name]) for name in settings.FEATURES}
            response = http.post("/predict", json=payload)
            response.raise_for_status()
            evidence["final_prediction"] = response.json()
        print(json.dumps(evidence, indent=2))
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=20)
        store.close()
        (settings.REPORTS_DIR / "verification.json").write_text(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    main()
