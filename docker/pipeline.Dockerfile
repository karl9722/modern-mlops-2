# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.8.0 AS uv

FROM python:3.11-slim-bookworm

# Java pour Spark
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY feature_repo ./feature_repo
COPY workspace.yaml dagster.yaml ./

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/artifacts /opt/dagster/home \
    && chown -R app:app /app /opt/dagster

ENV PATH="/app/.venv/bin:${PATH}" \
    PROJECT_ROOT=/app \
    DAGSTER_HOME=/opt/dagster/home

USER app