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
- A Postman/Newman API collection.
- Operating-system, device, and browser-version matrices; stress/soak profiles; and environment
  capacity tests.
- Threat modeling, penetration testing, and organization-specific security policy gates.
- Incident runbook and an example root-cause analysis.

## Delivered: Kubernetes browser, load, and security gates

- Three Playwright journeys on Chromium, Firefox, and WebKit through the kind-hosted frontend,
  covering authentication, viewer authorization and cited guidance, and the operator ticket
  lifecycle.
- A reproducible 30-second k6 profile with content/error checks and endpoint-specific p95
  latency thresholds against the same public boundary.
- CodeQL extended analysis across the repository's four code/workflow language families.
- Trivy dependency, secret, Docker/Terraform/Kubernetes configuration, and container-image
  gates, plus downloadable CycloneDX SBOMs for every runtime image.

These are regression-oriented baseline gates. Operating-system, device, and browser-version
matrices, stress/soak and production capacity measurements, threat modeling, and penetration
testing remain future environment-specific assurance work.

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

## Delivered: Kubernetes deployment

- Shared Kustomize resources for the five-service runtime and explicit local/production
  overlays.
- Restricted Pod Security, non-root execution, resource bounds, health probes,
  least-privilege service accounts, ingress NetworkPolicies, persistent state, and disruption
  controls.
- Production stateless replicas, CPU autoscaling, private-registry pulls, external runtime
  Secrets, a public LoadBalancer boundary, and a manually gated deploy/destroy workflow.
- Strict Kubernetes 1.36 schema validation and a disposable kind acceptance test covering
  the real event flow, RBAC denial, and PostgreSQL/Redpanda pod recovery.

Authentication, local role-based access, Azure deployment, analytics, the cited RAG baseline,
observability, and Kubernetes deployment are implemented. Kubernetes is verified in a real
disposable kind cluster; it is not a claim that the bundled single-replica PostgreSQL and
Redpanda data tier is highly available. The repository must not be described as
production-ready, continuously cloud-hosted, or multi-zone until those properties are
implemented and verified in the target environments.
