# Axon backend (FastAPI + uvicorn)
# Build from the repo root:  docker build -f backend/Dockerfile -t axon-backend .
#
# Multi-stage: wheels are built once in `builder`, then copied into a clean
# runtime image so build toolchains never ship in the final layer.

# ---- builder ---------------------------------------------------------------
FROM python:3.9-slim AS builder

WORKDIR /build

# Build wheels for every dependency (some google/crypto libs need a compiler).
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- runtime ---------------------------------------------------------------
FROM python:3.9-slim AS runtime

# Fail fast, no .pyc, unbuffered logs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install pre-built wheels (offline, no compiler needed here).
COPY backend/requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# App code.
COPY backend/ .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness against the public health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/').status==200 else sys.exit(1)"

# Shell form so $PORT is honoured if overridden at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
