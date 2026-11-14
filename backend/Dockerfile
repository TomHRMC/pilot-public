# Pilot for Trades Backend - Production-Ready Container
# Used for: Celery workers, Celery beat scheduler, and FastAPI server (future)
# Python Version: 3.14.3 (matches local development environment)
# Base Image Size: ~150MB (slim variant)

FROM python:3.14.3-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
# - gcc: Required for compiling Python C extensions
# - postgresql-client: For database health checks and psql commands
# - libpq-dev: PostgreSQL development headers (required by psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (leverages Docker layer caching)
# If requirements.txt doesn't change, this layer is reused
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Reduces image size by not storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# This layer rebuilds when any backend file changes
COPY . .

# Run as non-root (ALPHA-FIX-1) — same image serves worker, beat, and API.
# All pip install / apt-get steps remain above this USER switch (they need root).
# No port < 1024 is bound inside the container; uvicorn listens on 8000.
RUN useradd --create-home --uid 10001 pilot \
    && chown -R pilot:pilot /app
USER pilot

# Default command (overridden by docker-compose.yml service commands)
# This allows the same image to be used for worker, beat, and API server
CMD ["celery", "-A", "core.celery_app", "worker", "--loglevel=info"]

# Health check (optional - can be overridden in docker-compose.yml)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD celery -A core.celery_app inspect ping -d celery@$HOSTNAME || exit 1
