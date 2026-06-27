# Build from the repo root: docker build -f frontend/Dockerfile .
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/ .

ENV PYTHONUNBUFFERED=1
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
