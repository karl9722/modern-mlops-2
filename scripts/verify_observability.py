"""Verify provisioned Prometheus targets, alert rules, Grafana and read-only SQL access."""

import json
import os

import httpx
import psycopg

from mlops import settings


def main():
    targets = httpx.get("http://127.0.0.1:9090/api/v1/targets", timeout=10).json()
    target = next(
        t for t in targets["data"]["activeTargets"] if t["labels"]["job"] == "house-price-api"
    )
    assert target["health"] == "up", target.get("lastError")
    rules = httpx.get("http://127.0.0.1:9090/api/v1/rules", timeout=10).json()
    alerts = {r["name"] for group in rules["data"]["groups"] for r in group["rules"]}
    assert {
        "ApiDown",
        "ModelNotLoaded",
        "HighErrorRate",
        "HighLatency",
        "PredictionLogFailures",
    } <= alerts
    with httpx.Client(
        base_url="http://127.0.0.1:3001",
        timeout=15,
        auth=("admin", os.environ["GRAFANA_ADMIN_PASSWORD"]),
    ) as grafana:
        dashboard = grafana.get("/api/dashboards/uid/house-price-api")
        dashboard.raise_for_status()
        assert len(dashboard.json()["dashboard"]["panels"]) == 6
        for uid in ("prometheus", "monitoring-db"):
            health = grafana.get(f"/api/datasources/uid/{uid}/health")
            health.raise_for_status()
            assert health.json()["status"] == "OK", health.json()
    with psycopg.connect(
        host="127.0.0.1",
        port=os.getenv("POSTGRES_HOST_PORT", "5435"),
        dbname="monitoring",
        user="grafana_reader",
        password=os.environ["GRAFANA_DB_PASSWORD"],
    ) as conn:
        count = conn.execute("SELECT count(*) FROM monitoring_results").fetchone()[0]
        try:
            conn.execute("INSERT INTO monitoring_results DEFAULT VALUES")
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
        else:
            raise AssertionError("Grafana user unexpectedly has write privileges")
    evidence = {
        "prometheus_target": "up",
        "alert_rules": sorted(alerts),
        "grafana_panels": 6,
        "datasources": ["prometheus", "monitoring-db"],
        "monitoring_rows_visible": count,
        "grafana_reader_read_only": True,
    }
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (settings.REPORTS_DIR / "observability-verification.json").write_text(
        json.dumps(evidence, indent=2)
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
