FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OTEL_SDK_DISABLED=true \
    CONTRACTS_PATH=/app/contracts \
    DATASET_PATH=/app/ai-service/data/training_tickets.csv \
    KNOWLEDGE_PATH=/app/ai-service/knowledge

WORKDIR /app
RUN groupadd --gid 10001 serviceops \
    && useradd --uid 10001 --gid serviceops --no-create-home --shell /usr/sbin/nologin serviceops
COPY ai-service/pyproject.toml /app/ai-service/pyproject.toml
COPY ai-service/src /app/ai-service/src
RUN python -m pip install --upgrade pip==25.1.1 \
    && python -m pip install /app/ai-service
COPY --chown=10001:10001 ai-service/data /app/ai-service/data
COPY --chown=10001:10001 ai-service/knowledge /app/ai-service/knowledge
COPY --chown=10001:10001 contracts /app/contracts
RUN mkdir -p /app/model \
    && chown -R 10001:10001 /app/model

EXPOSE 8000
USER 10001:10001
CMD ["opentelemetry-instrument", "uvicorn", "serviceops_ai.app:app", "--host", "0.0.0.0", "--port", "8000"]
