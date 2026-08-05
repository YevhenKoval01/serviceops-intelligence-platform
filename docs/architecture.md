# Architecture

ServiceOps Intelligence is a compact event-driven support workflow. Spring Boot owns
the public business API and PostgreSQL data. The Python service owns the educational
machine-learning model. Kafka decouples ticket intake from prediction so operators do
not wait for inference before a ticket is stored. A read-oriented dbt layer turns immutable
ticket lifecycle history into tested PostgreSQL marts for the Power BI semantic model.

## Runtime topology

```mermaid
flowchart LR
    Operator[Support operator] -->|Credentials| UI[React + Nginx]
    UI -->|Login + authenticated REST| API[Spring Boot + Security]
    UI -->|Authenticated knowledge question| RAG[FastAPI retrieval assistant]
    KB[(Versioned Markdown runbooks)] -->|TF-IDF chunks| RAG
    API -->|BCrypt account lookup| DB
    API -->|Ticket + outbox transaction| DB[(PostgreSQL)]
    DB -->|Pending rows| Relay[Spring outbox relay]
    Relay -->|ticket.created.v1| Kafka[(Redpanda / Kafka API)]
    Kafka --> Worker[FastAPI + scikit-learn worker]
    Worker -->|ticket.prediction-completed.v1| Kafka
    Kafka --> API
```

| Service | Responsibility | Health signal |
| --- | --- | --- |
| `frontend` | Sign-in, role-aware operator queue, ticket creation, details, status changes, polling | Nginx `/health` |
| `backend` | Local identity, JWT issuance/validation, role enforcement, REST API, persistence, event production and prediction consumption | Actuator verifies application, PostgreSQL, and Kafka |
| `ai-service` | Shared JWT validation, cited knowledge retrieval, model loading, synchronous `/predict`, Kafka inference worker | `/health` requires the model, knowledge index, and broker-connected worker |
| `postgres` | Tickets, transactional event records, processed-event keys | `pg_isready` |
| `kafka` | Three versioned event topics | Redpanda cluster health |

## Analytics topology

```mermaid
flowchart LR
    API[Spring Boot] -->|Ticket + lifecycle transitions| DB[(PostgreSQL public schema)]
    Fixture[Deterministic fixture generator] -->|Opt-in 100,000 events| DB
    DB -->|Read operational sources| dbt[dbt build + data tests]
    dbt --> Staging[(analytics_staging)]
    Staging --> Facts[(analytics_intermediate)]
    Facts --> Marts[(analytics_mart)]
    Marts -->|Import model| PBI[Power BI TMDL semantic model]
```

Migration V4 records creation and every status change in `ticket_lifecycle_events` within
the same transaction as the ticket command. Repeating the current status is a no-op and
does not create a misleading lifecycle record. A transition away from `RESOLVED` is tagged
`REOPENED`. Existing V1-V3 tickets receive a `MIGRATED` snapshot at their last update time;
the warehouse exposes this lower-fidelity lineage instead of fabricating prior events.

dbt reads the application-owned tables and writes only to `analytics_*` schemas. The
performance mart has one row per ticket, priority-based first-response and resolution
deadlines, exact or qualified timestamps, current backlog age, breach flags, and reopen
counts. A separate daily mart supports category and priority trends. The Power BI model
keeps connection host/database as parameters and never stores credentials.

## Azure deployment topology

The cloud deployment preserves the same service and ownership boundaries while replacing
local infrastructure with managed Azure services:

```mermaid
flowchart LR
    Internet[Operator browser] -->|HTTPS| Web["Public Container App: React + Nginx"]
    subgraph VNet[Azure virtual network]
        subgraph ACA[Container Apps environment]
            Web -->|Internal HTTPS| API["Internal Spring Boot Container App"]
            Web -->|Internal HTTPS knowledge proxy| Worker["Internal FastAPI AI Container App"]
        end
        API -->|Private TLS| PG[(PostgreSQL Flexible Server)]
    end
    API -->|Kafka SASL/TLS| EH[(Azure Event Hubs)]
    EH -->|Kafka SASL/TLS| Worker
    Worker -->|Kafka SASL/TLS| EH
    Runbooks[(Bundled runbooks)] -->|Startup index| Worker
    ACR["Private Azure Container Registry"] -->|Pull-only managed identity| ACA
```

Terraform creates a workload-profile Container Apps environment on a dedicated subnet and
a separate delegated PostgreSQL subnet with private DNS. PostgreSQL has public network
access disabled. Spring and FastAPI have internal ingress, and only Nginx receives a public
HTTPS hostname. Nginx resolves both generated internal hostnames at container startup and
proxies authenticated `/assistant/` requests to the AI service.

Event Hubs remains reachable through its public Kafka endpoint but requires TLS plus a
namespace-scoped SAS credential. Its three event hubs are provisioned explicitly because
Event Hubs does not implement Kafka `AdminClient` topic management. Local Redpanda keeps
automatic topic creation enabled; the Azure backend disables only that behavior.

ACR administrator credentials are disabled. A shared user-assigned identity receives only
the `AcrPull` role and is used by Container Apps to fetch immutable images. Terraform
generates PostgreSQL, JWT, operator, and viewer secrets and stores them in encrypted Azure
Blob remote state and Container Apps secret values. Key Vault integration, external
identity, telemetry collection, managed analytics execution, Power BI publishing, and
Kubernetes are outside this deployment. The repository analytics can run against any
reachable PostgreSQL instance but is not silently provisioned by the Azure workflow.

## Ticket creation sequence

```mermaid
sequenceDiagram
    actor Operator
    participant UI as React
    participant API as Spring Boot
    participant DB as PostgreSQL
    participant Relay as Outbox relay
    participant K as Kafka
    participant ML as Python worker

    Operator->>UI: Submit validated ticket
    UI->>API: POST /api/tickets
    API->>DB: Insert ticket + outbox row
    DB-->>API: Commit
    API-->>UI: 201 Created
    Relay->>DB: Lock due rows (SKIP LOCKED)
    DB-->>Relay: Pending ticket.created event
    Relay->>K: Publish ticket.created v1
    K-->>Relay: Broker acknowledgement
    Relay->>DB: Mark event published
    K->>ML: Consume and validate JSON Schema
    ML->>ML: TF-IDF + LogisticRegression
    ML->>K: prediction-completed v1
    K->>API: Consume and validate envelope
    API->>DB: Update prediction + processed event in one transaction
    UI->>API: Poll ticket
    API-->>UI: Completed prediction
```

## Consistency and failure behavior

- Ticket and `ticket_events` outbox rows are persisted in one database transaction.
- The relay locks due unpublished rows with PostgreSQL `FOR UPDATE SKIP LOCKED`, allowing
  multiple backend instances to work without publishing the same row concurrently.
- A row is marked published only after Kafka acknowledges the send. Failures retain the
  payload, attempt count, next-attempt time, and last error for bounded exponential retry.
- Delivery is at least once: a crash after Kafka acknowledgement but before the database
  update can cause a replay. Stable event IDs and downstream idempotency make that safe.
- Both producers request idempotent Kafka delivery and wait for delivery confirmation.
- Python derives a deterministic prediction event ID from the input event ID. Replaying an
  input therefore produces the same downstream idempotency key.
- Spring stores prediction event IDs in `processed_events` in the same transaction as the
  ticket update. Replayed prediction events are ignored.
- Consumer processing is bounded. Invalid or exhausted events are published as structured
  records to `serviceops.ticket.invalid.v1` with failure and source context.
- Event topics and envelopes are versioned. JSON Schemas in `contracts/` reject unknown
  fields and constrain identifiers, timestamps, labels, and confidence.

When upgrading an existing database, migration V2 leaves historical event rows pending.
The relay may replay them once; the existing deterministic and idempotent consumers absorb
those duplicates while closing any pre-upgrade publication gap.

## Data ownership

Spring Boot is the normal writer to application tables, including `app_users`. Passwords are
stored only as BCrypt hashes. The AI service does not connect to PostgreSQL. The model
artifact is stored in the Compose `ai-model` volume and retrained only when a compatible
`baseline-1` artifact is absent. The explicitly invoked analytics fixture generator is the
only exception: it bulk-loads deterministic synthetic tickets and histories for validation.
dbt is read-only toward application tables and owns only its analytical schemas.

The AI service also owns the read-only knowledge index. Six tracked Markdown runbooks are
parsed into 18 heading-aware chunks at startup; their content and metadata produce a stable
index version digest. Query-time ranking combines word and phrase TF-IDF similarity, title
similarity, and lexical overlap. The extractive answer stage can use only retrieved source
sentences, labels each item with a citation number, and abstains when no passage crosses the
support gate. No user question or generated response is persisted.

## Security boundary

The React client exchanges a username and password only with Spring Boot. Spring Security
verifies a persisted BCrypt hash and returns a 15-minute HS256 JWT containing the subject,
issuer, audience, expiry, and role. The token lives in browser `sessionStorage`, is attached
to API requests, and is cleared on sign-out, expiry, or a `401` response. Spring and FastAPI
independently verify the same signature and claims.

Role policy is deliberately small:

| Capability | `VIEWER` | `OPERATOR` |
| --- | --- | --- |
| Read tickets and summary | Yes | Yes |
| Read model metadata | Yes | Yes |
| Ask cited knowledge questions | Yes | Yes |
| Create tickets and change status | No | Yes |
| Call direct `/predict` diagnostic | No | Yes |

Health checks and OpenAPI documents are public. Kafka consumers remain internal service
workloads and do not accept end-user credentials. Compose includes known non-secret local
accounts and a development signing key so a clean clone is reproducible; every value is
environment-configurable. The Azure deployment provides TLS ingress and managed
broker/database endpoints, but a production environment still requires external identity
or controlled account provisioning, Key Vault-backed secret rotation, token
refresh/revocation policy, stricter network egress and origin policy, dependency scanning,
and operational monitoring.
