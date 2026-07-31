# Roadmap

The current baseline is deliberately narrow: ticket intake, PostgreSQL persistence,
Kafka-based classification, an operator interface, health-gated local containers, and
automated quality checks. The phases below begin only after the baseline remains green.

## Phase 1.1: business workflow and analytics

- Authentication and role-based access.
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

## Phase 2: cloud and observability

- Azure Container Apps and Azure Database for PostgreSQL.
- Azure Event Hubs through its Kafka-compatible endpoint.
- Terraform infrastructure and controlled-cost demo lifecycle.
- OpenTelemetry instrumentation and production monitoring.

These are roadmap items, not implemented integrations. The repository must not be
described as authenticated, cloud-deployed, observable, or production-ready until the
corresponding work is complete and verified.
