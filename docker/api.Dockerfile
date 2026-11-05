# syntax=docker/dockerfile:1
ARG UV_VERSION=0.13.4
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# Stage 1 (builder): install dependencies into /app/.venv. Build tools stay in this stage.
FROM python:3.11-slim-bookworm@sha256:6cbe849bdc876ecd413a4a09a919a0d861d908589de9eba61e886c29af793a07 AS builder
COPY --from=uv /uv /bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first: this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=modern-mlops-2-uv,target=/root/.cache/uv \
    --mount=type=secret,id=proxy_ca \
    SSL_CERT_FILE="$(if [ -f /run/secrets/proxy_ca ]; then echo /run/secrets/proxy_ca; else echo /etc/ssl/certs/ca-certificates.crt; fi)" uv sync --frozen --no-dev --no-install-project
COPY . .
RUN --mount=type=cache,id=modern-mlops-2-uv,target=/root/.cache/uv \
    --mount=type=secret,id=proxy_ca \
    SSL_CERT_FILE="$(if [ -f /run/secrets/proxy_ca ]; then echo /run/secrets/proxy_ca; else echo /etc/ssl/certs/ca-certificates.crt; fi)" uv sync --frozen --no-dev --no-editable

# Stage 2 (runtime): a clean image with only the virtual environment copied in.
FROM python:3.11-slim-bookworm@sha256:6cbe849bdc876ecd413a4a09a919a0d861d908589de9eba61e886c29af793a07
# Run as a normal user, not root: limits the damage if the app is compromised.
RUN python -m pip uninstall -y setuptools wheel \
    && useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/app
ARG CODE_VERSION=unknown
ENV CODE_VERSION=${CODE_VERSION}
USER app
EXPOSE 8000
# Docker marks the container unhealthy if /health stops answering.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
CMD ["uvicorn", "mlops.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
