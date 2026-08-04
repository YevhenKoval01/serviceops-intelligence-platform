FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /analytics
COPY pyproject.toml .
COPY src src
RUN python -m pip install --upgrade pip==25.1.1 \
    && python -m pip install .
COPY dbt dbt

WORKDIR /analytics/dbt
CMD ["dbt", "build", "--profiles-dir", "."]
