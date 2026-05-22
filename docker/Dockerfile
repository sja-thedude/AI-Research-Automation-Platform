# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# NeuraForge AI — application image (used by web, worker, beat services)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#  - libpq for psycopg, tesseract for OCR, poppler for PDF rendering,
#  - build-essential for any wheels that need compiling.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        tesseract-ocr \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
ARG REQUIREMENTS=requirements/prod.txt
COPY requirements/ requirements/
RUN pip install -r ${REQUIREMENTS}

COPY . .

# Non-root runtime user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command runs the ASGI server (HTTP + WebSocket). Compose overrides
# this for the worker/beat services.
CMD ["gunicorn", "config.asgi:application", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
