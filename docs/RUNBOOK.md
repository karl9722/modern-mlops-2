# House Price API: Runbook

## Service level objectives (measured over 7 days)

| SLO | Target | Where to see it |
|---|---|---|
| Availability | ≥ 99% of /predict requests return non-5xx | Grafana: requests by status |
| Latency | p95 /predict < 200 ms | Grafana: p95 latency; HighLatency alert |
| Monitoring freshness | monitoring_job succeeded in the last 26 h | Dagster: runs |
| Model quality | live RMSE ≤ 1.5 × holdout RMSE | Grafana: latest monitoring checks |

## Daily operations

- Start: `docker compose up -d`. Stop: `docker compose down` (never add `-v` unless you mean to delete all data)
- Status: `docker compose ps`, `docker compose exec api mlops-model status`
- Logs: `docker compose logs -f api` (JSON; search by `request_id`)

## Release a new model

1. Run `training_job` in Dagster (or wait for Monday's scheduled run).
2. In MLflow, read the new version's `model_card.md` and gate tags.
3. `docker compose exec api mlops-model promote`
4. `docker compose restart api`
5. `uv run python scripts/smoke_test.py --api-key <key>`: every line must be PASS.
6. Watch the dashboard for 15 minutes.

## Roll back a model

1. `docker compose exec api mlops-model rollback` (or `--version <n>`)
2. `docker compose restart api`
3. Smoke test. Confirm `/ready` shows the expected version.

## Alert → action

| Alert / signal | First checks | Typical fix |
|---|---|---|
| ApiDown | `docker compose ps`, `docker compose logs api` | Restart api; check memory limits |
| ModelNotLoaded | `docker compose logs api`; is MLflow healthy? does a champion exist? | Fix MLflow, promote a version, restart api |
| HighErrorRate | API logs for exceptions (search `"level": "ERROR"`) | Roll back the model if it started after a release |
| HighLatency | CPU/memory (`docker stats`); is a training run active? | Wait for training to finish; investigate slow requests |
| PredictionLogFailures | `docker compose ps postgres`, Postgres logs | Restart Postgres; check disk space |
| input_drift failed | Open the HTML drift report in `artifacts/reports/` | Investigate which features drifted; retrain if the change is real |
| live_rmse failed | Compare predictions and feedback in Postgres | Retrain on recent data; roll back if a recent release caused it |
| Validation failed in training_job | `artifacts/reports/validation.json` | Fix or reject the source data. Never loosen a rule just to make it pass |

## Backups

    docker compose exec -T postgres pg_dumpall -U postgres > backup-$(date +%F).sql
    docker run --rm -v modern-mlops-2_mlflow-artifacts:/data -v "$PWD":/backup alpine:3.20 \
      tar czf /backup/mlflow-artifacts-$(date +%F).tgz -C /data .

For a non-destructive restore rehearsal, back up the application database and restore
into a new database on the development stack:

```bash
docker compose exec -T postgres pg_dump -U postgres -Fc monitoring > artifacts/monitoring.dump
docker compose exec postgres createdb -U postgres monitoring_restore
docker compose exec -T postgres pg_restore -U postgres --exit-on-error \
  -d monitoring_restore < artifacts/monitoring.dump
docker compose exec postgres psql -U postgres -d monitoring_restore \
  -c 'SELECT count(*) FROM predictions'
```

Compare counts with the source database before removing the rehearsal database. Never
overwrite the live database to test a backup. Dumps contain sensitive data and role
password hashes: keep them outside Git and outside the Docker build context.
`scripts/verify_operations.py` automates a restore into a unique temporary database,
compares prediction counts, then drops only that temporary database.

The MLflow artifacts volume must also be archived and restored into a separate volume;
a database dump alone cannot restore model files. Keep the registry database and its
artifact backup together. Do not assume files are recoverable until the restore is tested.

## Rotate an API key

1. Add the new key to `API_KEYS` (comma-separated), `docker compose up -d api`.
2. Move clients to the new key.
3. Remove the old key, `docker compose up -d api`.

## Retraining and skipped checks

- Training runs every Monday at 06:00 UTC and creates a candidate only.
- Monitoring runs every day at 07:00 UTC. Investigate failures before retraining manually.
- Promotion requires passing gate tags and a person reviewing the model card.
- Insufficient prediction/feedback volume is recorded with `passed = NULL` and a
  `details.skipped` reason. It is not a successful check and does not prove freshness.
- After a release, roll back when error rate, latency or labelled accuracy deteriorates.
- `scripts/verify_tp.py` and `scripts/verify_operations.py` are development exercises,
  not production operations: they deliberately change aliases/data and stop PostgreSQL.

## Startup and persistence

The sole stack definition is `docker-compose.yml`; previous split Compose definitions
were consolidated to avoid different services/configurations depending on the command.
All containers, images and volumes use the `modern-mlops-2` project identity.
Services are local-only: API 8001, MLflow 5000, Dagster 3000, Prometheus 9090,
Grafana 3001, PostgreSQL 5435 by default. Named volumes retain the registry, artifacts,
Dagster storage, Feast registry, Grafana and Prometheus across `docker compose down`.

Generate local credentials once with `uv run python scripts/init_env.py`. This preserves
an existing `.env`, creates data directories and never prints generated secret values.
Use `uv run --all-groups --env-file .env python scripts/smoke_test.py` so an API key need
not be placed in command arguments. Targets above are objectives, not measured guarantees.
