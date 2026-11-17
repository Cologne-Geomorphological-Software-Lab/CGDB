# syntax=docker/dockerfile:1
#
# CGDB demo image, used by compose.demo.yml. Not a production setup: it runs
# Django's development server with DEBUG on (see docker/demo_settings.py).

# --- Frontend: build the map bundle into static/dist ------------------------
FROM node:22.14.0-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Python dependencies from uv.lock ----------------------------------------
FROM python:3.15-slim-trixie AS python-deps
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- Runtime ----------------------------------------------------------------
FROM python:3.15-slim-trixie

# GDAL/GEOS/PROJ for GeoDjango, libpq for psycopg, and a PostgreSQL client
# new enough to back up the PostGIS 16 server (Debian trixie ships 17).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        gdal-bin \
        libpq5 \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# The app runs from /opt/venv, which uv builds without pip. The base image's
# own pip (with the urllib3 and msgpack it vendors) and setuptools are not
# used by anything here, but they are what Trivy keeps flagging, so remove
# them instead of chasing the base image's release cycle.
RUN python -m pip uninstall -y pip setuptools wheel

RUN useradd --create-home --uid 1000 cgdb \
    && mkdir -p /data \
    && chown cgdb:cgdb /data

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=prototype.settings \
    VITE_DEV_MODE=false \
    DAGSTER_HOME=/data/dagster_home

COPY --from=python-deps /opt/venv /opt/venv
WORKDIR /app
COPY --chown=cgdb:cgdb . .
COPY --from=frontend --chown=cgdb:cgdb /app/static/dist ./static/dist
COPY --chown=cgdb:cgdb docker/demo_settings.py prototype/local_settings.py
RUN chmod +x docker/entrypoint.sh

USER cgdb
EXPOSE 8000
VOLUME ["/data"]
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
