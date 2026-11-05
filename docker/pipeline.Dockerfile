# syntax=docker/dockerfile:1
ARG UV_VERSION=0.13.4
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.11-slim-bookworm@sha256:6cbe849bdc876ecd413a4a09a919a0d861d908589de9eba61e886c29af793a07 AS builder
COPY --from=uv /uv /bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=modern-mlops-2-uv,target=/root/.cache/uv \
    --mount=type=secret,id=proxy_ca \
    SSL_CERT_FILE="$(if [ -f /run/secrets/proxy_ca ]; then echo /run/secrets/proxy_ca; else echo /etc/ssl/certs/ca-certificates.crt; fi)" \
    uv sync --frozen --no-dev --group pipeline --no-install-project
COPY . .
RUN --mount=type=cache,id=modern-mlops-2-uv,target=/root/.cache/uv \
    --mount=type=secret,id=proxy_ca \
    SSL_CERT_FILE="$(if [ -f /run/secrets/proxy_ca ]; then echo /run/secrets/proxy_ca; else echo /etc/ssl/certs/ca-certificates.crt; fi)" \
    uv sync --frozen --no-dev --group pipeline --no-editable

FROM python:3.11-slim-bookworm@sha256:6cbe849bdc876ecd413a4a09a919a0d861d908589de9eba61e886c29af793a07
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y setuptools wheel \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/artifacts /app/feature_repo/data \
       /opt/dagster/home/storage /mlflow/artifacts \
    && chown -R app:app /app /opt/dagster /mlflow
WORKDIR /app
COPY --chown=app:app docker/dagster.yaml /opt/dagster/home/dagster.yaml
COPY --chown=app:app . /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/app \
    DAGSTER_HOME=/opt/dagster/home
ARG CODE_VERSION=unknown
ENV CODE_VERSION=${CODE_VERSION}
USER app
