# Roadmap

The current baseline is deliberately narrow: ticket intake, PostgreSQL persistence,
Kafka-based classification, an operator interface, health-gated local containers, and
automated quality checks. The phases below begin only after the baseline remains green.

## Phase 1.1: business workflow

- External identity federation, managed account lifecycle, and production token/key policy.
- SLA policies, deadlines, escalation, ownership, and audit views.

## Phase 1.2: AI quality

- SLA-breach prediction with a documented baseline comparison.
- Human review and approval workflow.
- Evaluation data, quality metrics, model and prompt versioning.
- Prompt-injection and unsafe-output tests.

## Delivered: retrieval-augmented knowledge assistant

- Six versioned, source-controlled operational runbooks split into heading-aware chunks.
- Reproducible TF-IDF retrieval with title weighting and lexical-support gating.
- Citation-bound extractive answers, an explicit unsupported-question abstention path, and
  authenticated access for both local roles.
- A fixed quality set covering 12 supported questions and 4 unrelated questions, plus
  local and Azure public-boundary smoke checks.

This is a controlled local RAG baseline without an external LLM, vector database, web search,
conversation memory, or automatic ingestion. Human approval and broader prompt-injection and
unsafe-output testing remain AI-quality roadmap work.

## Phase 1.3: reliability and QA

- Schema Registry or equivalent producer/consumer compatibility checks.
- Playwright browser flows and a Postman/Newman API collection.
- Load tests with measured latency and throughput.
- Dependency, container, and static security scanning.
- Incident runbook and an example root-cause analysis.

## Delivered: Azure deployment

- Azure Container Apps and Azure Database for PostgreSQL.
- Azure Event Hubs through its Kafka-compatible endpoint.
- Terraform infrastructure and controlled-cost demo lifecycle.
- GitHub OIDC deployment, immutable ACR builds, remote state, and cloud smoke test.

The implementation is deployable on demand and has an explicit destroy path. The
repository does not claim that a public demo is continuously hosted or that the topology
meets production availability requirements.

## Delivered: analytics

- Immutable ticket lifecycle history from Flyway V4 onward, with explicit migrated
  snapshots for older rows.
- Deterministic, idempotent generation of 100,000 non-sensitive lifecycle events.
- Tested dbt/PostgreSQL staging, lifecycle fact, ticket-performance, calendar, and daily
  category/priority marts.
- A source-controlled Power BI TMDL semantic model with SLA compliance, backlog age,
  first response, MTTR, reopen rate, and category trend measures.
- A dedicated CI gate that exercises the generator and full `dbt build` on PostgreSQL 17.

Analytical SLA thresholds are reporting assumptions, not an operational deadline,
notification, assignment, or escalation engine. Power BI publishing and scheduled refresh
require an explicitly configured Desktop/Fabric environment.

## Delivered: observability

- Pinned OpenTelemetry Java and Python instrumentation with W3C context propagation across
  HTTP, PostgreSQL, and Kafka, routed through an OpenTelemetry Collector.
- Prometheus metrics/rules, Loki logs, Tempo traces, Alertmanager routing, and a provisioned
  Grafana dashboard with metrics/logs/traces correlation.
- Rolling 30-day availability and latency objectives, explicit error budgets, checked burn
  alerts, a response runbook, and a deterministic firing/resolution notification drill.

The source-controlled overlay is a single-node validation topology, not a highly available
telemetry backend. Application instrumentation is portable: Azure can export to an explicitly
configured HTTPS OTLP endpoint, while access control, replicated storage, capacity, retention,
and the human notification provider remain deployment responsibilities.

Authentication, local role-based access, Azure deployment, analytics, and the cited RAG
baseline and observability are implemented and verified locally. Kubernetes remains roadmap
work, not a placeholder integration. The repository must not be described as production-ready,
highly available, or continuously cloud-hosted until the corresponding work is complete and
verified in an actual subscription.
