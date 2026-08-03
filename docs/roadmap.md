# Roadmap

The current baseline is deliberately narrow: ticket intake, PostgreSQL persistence,
Kafka-based classification, an operator interface, health-gated local containers, and
automated quality checks. The phases below begin only after the baseline remains green.

## Phase 1.1: business workflow and analytics

- External identity federation, managed account lifecycle, and production token/key policy.
- SLA policies, deadlines, escalation, ownership, and audit views.
- Reproducible generation of at least 100,000 ticket lifecycle events.
- Analytical PostgreSQL schema with dbt transformations and tests.
- Power BI measures for SLA compliance, backlog age, first response time, MTTR,
  reopen rate, and category trends.

## Phase 1.2: AI quality

- SLA-breach prediction with a documented baseline comparison.
- Retrieval-augmented knowledge assistant with citations.
- Human review and approval workflow.
- Evaluation data, quality metrics, model and prompt versioning.
- Prompt-injection and unsafe-output tests.

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

## Phase 2: observability

- OpenTelemetry instrumentation and trace context propagation.
- Production metrics, logs, traces, alerting, and dashboards.
- SLOs, error budgets, and a tested operational response process.

Authentication, local role-based access, and the Azure deployment capability are
implemented and verified locally. Analytics, RAG, observability, and Kubernetes remain
roadmap work, not placeholder integrations. The repository must not be described as
observable, production-ready, or continuously cloud-hosted until the corresponding work is
complete and verified in an actual subscription.
