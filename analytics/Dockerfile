FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /analytics
RUN groupadd --gid 10001 serviceops \
    && useradd --uid 10001 --gid serviceops --no-create-home --shell /usr/sbin/nologin serviceops
COPY pyproject.toml .
COPY src src
RUN python -m pip install --upgrade pip==25.1.1 \
    && python -m pip install .
COPY dbt dbt
RUN chown -R 10001:10001 /analytics

WORKDIR /analytics/dbt
USER 10001:10001
CMD ["dbt", "build", "--profiles-dir", "."]
