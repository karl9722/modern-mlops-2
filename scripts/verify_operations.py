"""Exercise database outage, alert firing and backup/restore on this Compose project.

Use only on an isolated development stack: this deliberately stops its PostgreSQL service.
The service is restarted in finally. No volume or production database is deleted.
Run: uv run --all-groups --env-file .env python scripts/verify_operations.py
"""

import json
import subprocess
import time

import httpx

from mlops import settings

SAMPLE = {
    "OverallQual": 7,
    "GrLivArea": 1800,
    "GarageCars": 2,
    "TotalBsmtSF": 900,
    "YearBuilt": 2005,
}


def compose(*args, **kwargs):
    return subprocess.run(["docker", "compose", *args], cwd=settings.ROOT, check=True, **kwargs)


def main():
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {}
    headers = {"X-API-Key": next(iter(settings.api_keys()))}
    with httpx.Client(base_url="http://127.0.0.1:8001", headers=headers, timeout=20) as http:
        http.get("/ready").raise_for_status()
        http.post("/predict", json=SAMPLE).raise_for_status()
        # Allow Prometheus to establish a baseline before the outage counter changes.
        print("Waiting for the metrics baseline before the outage exercise", flush=True)
        time.sleep(20)
        try:
            compose("stop", "postgres", capture_output=True)
            response = http.post("/predict", json=SAMPLE)
            response.raise_for_status()
            evidence["database_outage_prediction"] = response.json()
            for _ in range(30):
                alerts = httpx.get("http://127.0.0.1:9090/api/v1/alerts", timeout=5).json()
                found = [
                    a
                    for a in alerts["data"]["alerts"]
                    if a["labels"]["alertname"] == "PredictionLogFailures"
                    and a["state"] == "firing"
                ]
                if found:
                    evidence["prediction_log_failures_alert"] = "firing"
                    break
                time.sleep(3)
            assert evidence.get("prediction_log_failures_alert") == "firing"
        finally:
            compose("start", "postgres", capture_output=True)

        for _ in range(30):
            try:
                response = http.post("/predict", json=SAMPLE)
                response.raise_for_status()
                feedback = http.post(
                    "/feedback",
                    json={
                        "prediction_id": response.json()["prediction_id"],
                        "actual_sale_price": 210000,
                    },
                )
                if feedback.status_code == 201:
                    evidence["storage_recovered"] = True
                    break
            except httpx.TransportError:
                pass
            time.sleep(2)
        assert evidence.get("storage_recovered")

    backup = settings.REPORTS_DIR / "monitoring-backup.dump"
    with backup.open("wb") as output:
        compose(
            "exec",
            "-T",
            "postgres",
            "pg_dump",
            "-U",
            "postgres",
            "-Fc",
            "monitoring",
            stdout=output,
        )
    count_sql = "SELECT count(*) FROM predictions"
    original = compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "postgres",
        "-d",
        "monitoring",
        "-tAc",
        count_sql,
        capture_output=True,
    ).stdout.strip()
    # A new temporary database proves restore without replacing the running one.
    restore_db = "tp_restore_" + str(time.time_ns())
    compose("exec", "-T", "postgres", "createdb", "-U", "postgres", restore_db, capture_output=True)
    try:
        with backup.open("rb") as source:
            compose(
                "exec",
                "-T",
                "postgres",
                "pg_restore",
                "-U",
                "postgres",
                "--exit-on-error",
                "-d",
                restore_db,
                stdin=source,
                capture_output=True,
            )
        restored = compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "postgres",
            "-d",
            restore_db,
            "-tAc",
            count_sql,
            capture_output=True,
        ).stdout.strip()
        assert original == restored
        evidence["postgres_restore"] = {
            "predictions": int(restored),
            "backup_bytes": backup.stat().st_size,
        }
    finally:
        compose(
            "exec", "-T", "postgres", "dropdb", "-U", "postgres", restore_db, capture_output=True
        )
    (settings.REPORTS_DIR / "operations-verification.json").write_text(
        json.dumps(evidence, indent=2)
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
