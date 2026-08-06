# ServiceOps Intelligence Platform

ServiceOps Intelligence is an operator-facing support platform that stores incoming
tickets immediately and classifies them asynchronously. The core vertical slice connects
React, Spring Boot, PostgreSQL, Kafka, FastAPI, and a real scikit-learn model in one
locally reproducible system. Persisted BCrypt accounts and short-lived signed tokens protect
the operator workflow with read-only and mutating roles. Immutable lifecycle history, tested
dbt marts, and a Power BI semantic model provide reproducible service-performance analytics.
A citation-enforced knowledge assistant retrieves operational guidance from versioned local
runbooks and abstains when those sources do not support an answer.
An opt-in OpenTelemetry pipeline correlates metrics, logs, and distributed traces across
HTTP, PostgreSQL, and Kafka, with provisioned SLO dashboards and tested alert delivery.

> Project status: **Baseline complete - active development**

The machine-learning model is an educational baseline trained on a small bundled
synthetic dataset. Its measured validation scores are available from `/model-info`; they
must not be interpreted as production accuracy.

![ServiceOps operator workspace showing the live classified ticket queue](docs/images/serviceops-operator-workspace.png)

_Real local Compose runtime after ticket creation, asynchronous classification, and a
status update through the rendered React interface._

## Core event flow

```mermaid
sequenceDiagram
    actor Operator
    participant UI as React UI
    participant API as Spring Boot API
    participant DB as PostgreSQL
    participant Kafka as Redpanda (Kafka API)
    participant ML as FastAPI + scikit-learn

    Operator->>UI: Sign in
    UI->>API: POST /api/auth/login
    API->>DB: Verify BCrypt account
    API-->>UI: Short-lived signed bearer token
    Operator->>UI: Create ticket
    UI->>API: POST /api/tickets + bearer token
    API->>DB: Commit ticket + outbox event
    API-->>UI: 201 Created (prediction pending)
    API->>DB: Relay locks pending outbox rows
    API->>Kafka: ticket.created.v1
    Kafka-->>API: Broker acknowledgement
    API->>DB: Mark outbox event published
    Kafka->>ML: Consume ticket event
    ML->>ML: TF-IDF + LogisticRegression
    ML->>Kafka: ticket.prediction-completed.v1
    Kafka->>API: Consume prediction
    API->>DB: Store prediction idempotently
    UI->>API: Poll GET /api/tickets/{id}
    API-->>UI: Ticket with category, priority, confidence
```

The event row is a durable outbox entry committed in the same PostgreSQL transaction as
the ticket. A scheduled relay locks due rows with `FOR UPDATE SKIP LOCKED`, waits for Kafka
acknowledgement, and only then records publication. Failed attempts remain durable and are
retried with bounded exponential backoff.

Every ticket creation and real status transition is also retained in PostgreSQL. An opt-in,
deterministic 100,000-event fixture feeds dbt models for SLA compliance, backlog age, first
response time, MTTR, reopen rate, and category trends. Normal application startup never
loads this analytical fixture.

## Grounded knowledge assistant

The operator and viewer workspaces include an authenticated knowledge assistant for access,
billing, delivery, API, performance, and incident procedures. FastAPI loads six
source-controlled Markdown runbooks, splits them into 18 heading-aware chunks, and builds a
reproducible TF-IDF index at startup. Retrieval combines content and title relevance with a
lexical-support gate. A deterministic extractive generator selects only sentences from the
retrieved chunks and adds a numbered citation to every answer item.

Unsupported questions return an explicit human-review response with no citations; the
assistant does not use general model knowledge to fill gaps. The fixed evaluation set covers
12 answerable questions and 4 unrelated questions. This is a deliberately small, local RAG
baseline: it has no external LLM dependency, vector database, web search, conversation memory,
or automatic document ingestion.

## Technology choices

| Component | Role |
| --- | --- |
| React 19, TypeScript, Vite | Responsive operator queue, ticket form, details, and status changes |
| Spring Boot Security, BCrypt, JWT | Persisted local identity and `VIEWER`/`OPERATOR` role enforcement |
| Spring Boot 3, Java 21 | Validated business API and event orchestration |
| Spring Data JPA, Hibernate, Flyway | Domain persistence and versioned schema migration |
| PostgreSQL 17 | Durable ticket, transactional outbox, and consumer-idempotency data |
| Redpanda | Pinned local Kafka-protocol broker with three versioned topics |
| FastAPI, scikit-learn, pandas | HTTP model inspection plus asynchronous ticket inference |
| TF-IDF retrieval, versioned Markdown runbooks | Deterministic grounded answers with per-claim citations and abstention |
| dbt Core, dbt-postgres | Tested PostgreSQL lifecycle, SLA-performance, calendar, and daily trend marts |
| Power BI TMDL | Source-controlled semantic model and operational DAX measures |
| Docker Compose | Health-gated local topology for all five services |
| Azure Container Apps, PostgreSQL, Event Hubs, ACR | Terraform-managed cloud runtime with private data and public frontend ingress |
| GitHub Actions | Independent Java, Python, frontend, Terraform, container image, and manual Azure deployment jobs |
| OpenTelemetry Java/Python + Collector | Portable OTLP instrumentation, W3C context propagation, and trace-derived RED metrics |
| Prometheus, Alertmanager, Grafana, Loki, Tempo | SLO records, error budgets, alert routing, dashboards, logs, and traces |

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
- Knowledge API: <http://localhost:8000/docs> (`POST /knowledge/ask`)

Sign in to the UI with one of the known local-development accounts:

- `operator` / `operator_dev_2026` - read, create, and update tickets.
- `viewer` / `viewer_dev_2026` - read-only ticket and model access.

These are deliberately non-secret local defaults. Override both passwords and the shared
JWT signing key through `.env` before using the stack outside an isolated development
machine. Existing bootstrap accounts are never overwritten on restart.

Stop containers without deleting the PostgreSQL volume:

```bash
docker compose down
```

Delete all local application data only when explicitly desired:

```bash
docker compose down --volumes
```

## Observe locally

Observability is opt-in so normal application startup stays lightweight:

```bash
docker compose \
  -f compose.yaml \
  -f compose.observability.yaml \
  up --build --detach --wait
python scripts/smoke_test.py
python scripts/observability_smoke_test.py
```

Open the provisioned dashboard at <http://localhost:3001/d/serviceops-overview> with
`admin` / `serviceops_observe_2026`. Prometheus scrapes bounded application SLI metrics while
Spring and FastAPI export OTLP logs and traces; the Collector also derives RED metrics from
spans. W3C trace context crosses HTTP and Kafka (with a producer-to-consumer span link),
traces link to logs, rolling 30-day availability and latency objectives are recorded, and
checked alerts route through Alertmanager. The deterministic drill additionally proves
firing and resolved notifications. See the [observability guide](observability/README.md) and
[response runbook](docs/observability-runbook.md).

## Deploy to Azure

The manual `Azure deployment` GitHub Actions workflow provisions a controlled-cost demo
topology with Terraform. It builds immutable images in ACR, deploys the frontend, backend,
and AI worker to a VNet-integrated Container Apps environment, uses private PostgreSQL
Flexible Server storage, and replaces local Redpanda with three Event Hubs exposed through
the Kafka-compatible TLS endpoint. Only the frontend has public ingress.

The workflow uses GitHub-to-Azure OIDC, encrypted remote state, generated application
credentials, and a pull-only managed identity for ACR. A normal push never provisions or
changes cloud resources. See the [Azure deployment guide](infra/azure/README.md) for the
required repository secrets, variables, permissions, deploy sequence, credential handling,
and explicit destroy procedure.

This repository contains and validates the deployment capability; it does not claim an
always-on public environment. Running the workflow creates billable Azure resources until
the matching destroy action completes.

## Build analytics locally

Analytics is opt-in and runs against the PostgreSQL schema migrated by the backend:

```bash
docker compose up --build --detach --wait
docker compose --profile analytics build analytics
docker compose --profile analytics run --rm analytics serviceops-generate-analytics
docker compose --profile analytics run --rm analytics
```

The generator produces exactly 100,000 deterministic, non-sensitive lifecycle events by
default. The final analytics command executes `dbt build`, including every model and data
test. See the [analytics guide](analytics/README.md) for metric definitions, idempotency,
environment overrides, migrated-history semantics, and Power BI model usage.

## Demonstration

1. Open the UI and sign in as the local operator.
2. Create a ticket with a meaningful title and description.
3. The row appears immediately with an `Analyzing…` state.
4. Spring stores the ticket and outbox event atomically; the relay publishes
   `serviceops.ticket.created.v1` and records the broker acknowledgement.
5. The AI worker validates the event and emits `serviceops.ticket.prediction-completed.v1`.
6. Spring validates and persists the idempotent prediction.
7. The UI poll updates the row and detail panel with category, priority, and confidence.
8. Change the status from the detail panel to verify the command path.
9. Ask the knowledge assistant how to triage repeated API errors and inspect its citations.

The standard-library smoke test automates the same public API flow:

```bash
python scripts/smoke_test.py
```

## Run tests

Backend (Java 21 and Maven 3.9+):

```bash
cd backend
mvn --batch-mode --no-transfer-progress verify
```

The PostgreSQL repository integration test uses Testcontainers and requires a working
Docker engine.

AI service (Python 3.12+):

```bash
cd ai-service
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"  # Windows
.venv/Scripts/python -m ruff check src tests ../scripts/cloud_smoke_test.py
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

Azure infrastructure (Terraform 1.15.8):

```bash
terraform -chdir=infra/azure fmt -check -recursive
terraform -chdir=infra/azure init -backend=false
terraform -chdir=infra/azure validate
terraform -chdir=infra/azure test
```

Analytics (Python 3.12+, PostgreSQL 17):

```bash
cd analytics
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts
python -m pytest
python scripts/validate_power_bi_model.py
dbt build --project-dir dbt --profiles-dir dbt
```

## Public API

- `POST /api/auth/login` (public credential exchange)
- `GET /api/auth/me` (authenticated identity)
- `POST /api/tickets`
- `GET /api/tickets`
- `GET /api/tickets/{id}`
- `PATCH /api/tickets/{id}/status`
- `GET /api/summary`
- `GET /actuator/health`
- `GET /actuator/prometheus`
- `POST /predict`
- `GET /health`
- `GET /model-info`
- `GET /metrics`
- `POST /knowledge/ask` (direct AI-service route)
- `POST /assistant/ask` (same-origin frontend proxy used by the UI)

Health and OpenAPI endpoints remain public for container orchestration and API discovery.
All business endpoints require a signed bearer token. `VIEWER` can read tickets, summary,
model metadata, and cited knowledge answers; `OPERATOR` additionally creates tickets,
changes status, and calls the direct model prediction endpoint.

JSON Schema contracts live in [`contracts`](contracts). Invalid consumer messages are
sent to `serviceops.ticket.invalid.v1`, and consumers use bounded retries or explicit
invalid-message handling.

## Technical documentation

- [Architecture and reliability behavior](docs/architecture.md)
- [API requests, responses, and error examples](docs/api-examples.md)
- [Test strategy and acceptance procedure](docs/test-strategy.md)
- [Phased roadmap](docs/roadmap.md)
- [Azure deployment and teardown](infra/azure/README.md)
- [Analytics pipeline, metrics, and Power BI model](analytics/README.md)
- [Observability stack, objectives, and validation](observability/README.md)
- [Observability response runbook](docs/observability-runbook.md)

## Verified baseline

The latest local regression on 6 August 2026 measured:

- Java: 34 tests passed, including Spring Security role enforcement, PostgreSQL 17,
  Flyway V1-V4, lifecycle history, JPA, JSONB, outbox retry state, and concurrent row
  locking through Testcontainers.
- Python: Ruff passed and 24 pytest tests passed, including shared JWT validation, RAG
  retrieval/abstention evaluation, and Event Hubs Kafka profile validation.
- Frontend: ESLint passed, 19 Vitest tests passed, TypeScript compiled, and the Vite
  production bundle completed.
- Analytics: Ruff passed and 4 pytest tests passed; the fixed fixture generated 40,000
  tickets and exactly 100,000 lifecycle events; dbt built 6 models and passed all 52 data
  tests on PostgreSQL 17; the 59-pass build had zero warnings or errors; the Power BI TMDL
  contract contained all 6 required measures. Repeating the fixture inserted zero rows and
  reproduced SHA-256 `f2d50639d79b9ac3d0b20a1a246f40c67cb0060fa320f6ba3cf12a861f2fd464`.
- Compose: configuration validation passed; all four images built; PostgreSQL, Redpanda,
  Spring Boot, FastAPI, and React/Nginx reported healthy; the opt-in analytics image loaded
  the full fixture and completed its own green `dbt build`.
- Observability: all 12 long-running services reported healthy and the non-root data-volume
  initializer exited successfully; all seven Prometheus scrape targets were up, 17 checked
  recording/alerting rules loaded, and the fixed rule tests passed. The runtime smoke test
  proved both applications' SLI and trace-derived metrics, OTLP logs and traces, the Kafka
  producer-to-consumer span link, provisioned Grafana assets, firing webhook delivery,
  recovery, and resolved delivery.
- End to end: the authenticated smoke test passed from a clean application volume, including
  a cited RAG answer and unrelated-question abstention through Nginx; its runtime ticket
  retained ordered `CREATED` and `STATUS_CHANGED` lifecycle rows.
- Authentication: anonymous access returned `401`; the viewer could read but received
  `403` for Spring and FastAPI mutations; the operator token worked across both services;
  bootstrap passwords were stored as BCrypt hashes.
- Runtime reliability: both event topics were inspected, prediction replay was idempotent,
  malformed input reached the structured invalid-event topic, PostgreSQL/backend restarts
  preserved a ticket, the persisted model hash survived an AI-service restart, and an
  outbox event created during a Kafka outage was delivered after both broker recovery and
  a backend process restart.
- Browser: the grounded answer and two source cards rendered through the real application;
  ticket creation, prediction polling, accessible detail display, and status update remained
  available with no browser console warnings or errors.
- Azure deployment: Terraform 1.15.8 formatting and AzureRM 4.81.0 schema validation
  passed; the credential-free mocked plan test verified the network/ingress/identity
  boundaries; actionlint passed for both workflows; and the cloud-style smoke script passed
  through the public Nginx boundary. No paid Azure resources were created in this local run.
- Model: 40 synthetic training rows; the fixed held-out split measured `0.60` category
  accuracy and `0.50` priority accuracy. These small-sample scores are reproducibility
  evidence, not production performance claims.

## Current limitations

- The synthetic model dataset is deliberately small and non-production.
- Kubernetes remains roadmap work and is not represented as complete.
- The checked observability topology is single-node and validated locally, not a claim of a
  highly available or capacity-tested telemetry control plane. Production use requires an
  approved external alert receiver, protected access, replicated durable storage, and an
  environment-specific retention/capacity plan.
- The bundled knowledge base is intentionally small and manually curated. The RAG baseline
  uses deterministic extractive generation rather than a general-purpose LLM; automatic
  ingestion, conversation memory, human approval, and broader prompt-safety evaluation remain
  roadmap work.
- The Power BI semantic model and measures are source controlled, but cross-platform CI does
  not claim a Desktop/Fabric refresh or a published dashboard. Operational SLA enforcement,
  escalation, and ownership workflows remain separate roadmap work.
- Azure deployment is implemented as validated Terraform and a manual deploy/destroy
  workflow, but no always-on hosted environment or production availability claim is made.
  Event Hubs and ACR use authenticated public endpoints, while PostgreSQL is private.
- Authentication uses local bootstrap accounts and short-lived access tokens. External
  identity federation, self-service account lifecycle, refresh/revocation flows, and a
  managed secret store remain roadmap work. Local Compose still uses development HTTP;
  Azure application ingress and managed service connections use TLS.
- Browser-engine automation, load measurements, and security scanning are for next phase work;
  the current cross-service smoke test uses authenticated HTTP APIs.
