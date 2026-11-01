# Dockerfile cho ChurnGuard MLOps Serving Service
FROM python:3.11-slim

WORKDIR /app

# Cai dat dependencies he thong
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chep source code va model artifacts
COPY src/ /app/src/
COPY data/models/ /app/data/models/
COPY data/processed/ /app/data/processed/
COPY data/feast_repo/ /app/data/feast_repo/
COPY DESIGN.md /app/

RUN groupadd -g 10001 appgroup && useradd -u 10001 -g appgroup -s /bin/sh appuser && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
