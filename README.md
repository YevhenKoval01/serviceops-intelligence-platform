# ServiceOps Intelligence Platform

ServiceOps Intelligence is an operator-facing support platform that stores incoming
tickets immediately and classifies them asynchronously. The core vertical slice connects
React, Spring Boot, PostgreSQL, Kafka, FastAPI, and a real scikit-learn model in one
locally reproducible system.

> Project status: **Baseline initialized - baseline polish still in progress**

The machine-learning model is an educational baseline trained on a small bundled
synthetic dataset. Its measured validation scores are available from `/model-info`; they
must not be interpreted as production accuracy.

## Core event flow

```mermaid
sequenceDiagram
    actor Operator
    participant UI as React UI
    participant API as Spring Boot API
    participant DB as PostgreSQL
    participant Kafka as Redpanda (Kafka API)
    participant ML as FastAPI + scikit-learn

    Operator->>UI: Create ticket
    UI->>API: POST /api/tickets
    API->>DB: Store ticket + event record
    API-->>UI: 201 Created (prediction pending)
    API->>Kafka: ticket.created.v1
    Kafka->>ML: Consume ticket event
    ML->>ML: TF-IDF + LogisticRegression
    ML->>Kafka: ticket.prediction-completed.v1
    Kafka->>API: Consume prediction
    API->>DB: Store prediction idempotently
    UI->>API: Poll GET /api/tickets/{id}
    API-->>UI: Ticket with category, priority, confidence
```

The event row is committed in the same PostgreSQL transaction as the ticket. 

## Technology choices

| Component | Role |
| --- | --- |
| React 19, TypeScript, Vite | Responsive operator queue, ticket form, details, and status changes |
| Spring Boot 3, Java 21 | Public validated API and event orchestration |
| Spring Data JPA, Hibernate, Flyway | Domain persistence and versioned schema migration |
| PostgreSQL 17 | Durable ticket, event, and consumer-idempotency data |
| Redpanda | Pinned local Kafka-protocol broker with three versioned topics |
| FastAPI, scikit-learn, pandas | HTTP model inspection plus asynchronous ticket inference |
| Docker Compose | Health-gated local topology for all five services |

## Run locally

Requirements: Docker with Compose v2 and at least 4 GB of available memory.

```bash
cp .env.example .env
docker compose up --build
```

Safe development defaults are already present in `compose.yaml`; `.env` is optional and
ignored by Git. Open:

- Operator UI: <http://localhost:3000>
- Spring OpenAPI: <http://localhost:8080/swagger-ui.html>
- Spring health: <http://localhost:8080/actuator/health>
- FastAPI OpenAPI: <http://localhost:8000/docs>
- Model metadata: <http://localhost:8000/model-info>

Stop containers without deleting the PostgreSQL volume:

```bash
docker compose down
```

Delete all local application data only when explicitly desired:

```bash
docker compose down --volumes
```

## Demonstration

1. Open the operator UI and create a ticket with a meaningful title and description.
2. The row appears immediately with an `Analyzing…` state.
3. Spring stores the ticket and event, then publishes `serviceops.ticket.created.v1`.
4. The AI worker validates the event and emits `serviceops.ticket.prediction-completed.v1`.
5. Spring validates and persists the idempotent prediction.
6. The UI poll updates the row and detail panel with category, priority, and confidence.
7. Change the status from the detail panel to verify the command path.

The standard-library smoke test automates the same public API flow:

```bash
python scripts/smoke_test.py
```

## Run tests

Backend (Java 21 and Maven 3.9+):

```bash
cd backend
mvn test
```

AI service (Python 3.12+):

```bash
cd ai-service
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"  # Windows
.venv/Scripts/python -m ruff check src tests
.venv/Scripts/python -m pytest
```

On Linux or macOS, replace `.venv/Scripts/python` with `.venv/bin/python`.

Frontend (Node.js 22+):

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

## Public API

- `POST /api/tickets`
- `GET /api/tickets`
- `GET /api/tickets/{id}`
- `PATCH /api/tickets/{id}/status`
- `GET /api/summary`
- `GET /actuator/health`
- `POST /predict`
- `GET /health`
- `GET /model-info`

JSON Schema contracts live in [`contracts`](contracts). Invalid consumer messages are
sent to `serviceops.ticket.invalid.v1`, and consumers use bounded retries or explicit
invalid-message handling.

## Current limitations

- Ticket-created publication is post-commit, not yet driven by a durable outbox relay.
- The synthetic model dataset is deliberately small and non-production.
- CI, clean-state double-run evidence, repository screenshot, expanded documentation,
  additional integration tests, and final error-handling polish in progress.
- Authentication, cloud deployment, analytics, RAG, observability, and Kubernetes are
  roadmap work and are not represented as complete.
