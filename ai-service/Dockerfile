FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONTRACTS_PATH=/app/contracts \
    DATASET_PATH=/app/ai-service/data/training_tickets.csv

WORKDIR /app
COPY ai-service/pyproject.toml /app/ai-service/pyproject.toml
COPY ai-service/src /app/ai-service/src
RUN python -m pip install --upgrade pip==25.1.1 \
    && python -m pip install /app/ai-service
COPY ai-service/data /app/ai-service/data
COPY contracts /app/contracts

EXPOSE 8000
CMD ["uvicorn", "serviceops_ai.app:app", "--host", "0.0.0.0", "--port", "8000"]
