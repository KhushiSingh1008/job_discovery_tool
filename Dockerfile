# syntax=docker/dockerfile:1
#
# One image for production: the FastAPI app serves the API and the built React app, and
# scrapes on a schedule. SQLite lives on a mounted disk at /data.

# ---- 1. Build the React app -------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python runtime ------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GG_DATABASE_PATH=/data/jobs.db \
    GG_STATIC_DIR=/app/static \
    GG_SCRAPE_INTERVAL_HOURS=24

WORKDIR /app

# Dependencies first, from pyproject.toml alone, so code changes reuse this layer.
COPY backend/pyproject.toml ./
RUN python -c "import subprocess, sys, tomllib; \
deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; \
subprocess.check_call([sys.executable, '-m', 'pip', 'install', *deps])"

COPY backend/app ./app
COPY --from=frontend /frontend/dist ./static
# Snapshot of scraped listings: a fresh disk (or the free plan's ephemeral one) starts
# with jobs instead of an empty page while the first scrape runs.
COPY backend/seed/jobs.db ./seed/jobs.db

# Run as an unprivileged user that owns only the data directory.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin gradguide \
    && mkdir -p /data && chown gradguide /data
USER gradguide

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# One worker: SQLite and the in-process scheduler expect a single process.
# --proxy-headers: client IPs come from the platform's load balancer (for rate limits).
CMD ["sh", "-c", "[ -f \"$GG_DATABASE_PATH\" ] || cp /app/seed/jobs.db \"$GG_DATABASE_PATH\"; exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
