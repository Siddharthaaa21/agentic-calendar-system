# Axon frontend (Streamlit)
# Build from the repo root:  docker build -f frontend/Dockerfile -t axon-frontend .
#
# Shares backend/requirements.txt (single dependency set for the whole project).

# ---- builder ---------------------------------------------------------------
FROM python:3.9-slim AS builder

WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- runtime ---------------------------------------------------------------
FROM python:3.9-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY backend/requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

COPY frontend/ .

RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

# Streamlit ships a health endpoint at /_stcore/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').status==200 else sys.exit(1)"

CMD streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT}
