#!/bin/sh
set -eu

# psql quotes literal values, including passwords containing quotes or punctuation.
psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname postgres <<'EOSQL'
\getenv mlflow_password MLFLOW_DB_PASSWORD
\getenv dagster_password DAGSTER_DB_PASSWORD
\getenv app_password APP_DB_PASSWORD
\getenv grafana_password GRAFANA_DB_PASSWORD
CREATE USER mlflow WITH PASSWORD :'mlflow_password';
CREATE DATABASE mlflow OWNER mlflow;
CREATE USER dagster WITH PASSWORD :'dagster_password';
CREATE DATABASE dagster OWNER dagster;
CREATE USER app WITH PASSWORD :'app_password';
CREATE DATABASE monitoring OWNER app;
CREATE USER grafana_reader WITH PASSWORD :'grafana_password';
GRANT CONNECT ON DATABASE monitoring TO grafana_reader;
EOSQL

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname monitoring <<'EOSQL'
GRANT USAGE ON SCHEMA public TO grafana_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE app IN SCHEMA public GRANT SELECT ON TABLES TO grafana_reader;
EOSQL
