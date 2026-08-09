# Test strategy

The baseline uses a small test pyramid: deterministic unit tests are the fastest
feedback, focused integration tests cover framework and database behavior, and the
Compose smoke test proves the real cross-service flow.

## Quality layers

| Layer | Coverage |
| --- | --- |
| Java unit and web slice | Login exchange, anonymous `401`, viewer `403`, request normalization and validation, RFC 7807 errors, transactional outbox state and retries, acknowledged Kafka delivery, prediction contract validation and idempotency, structured dead-letter records |
| Java repository integration | Real PostgreSQL 17 container, Flyway schema validation through V4, BCrypt account record, JPA ticket and lifecycle persistence, JSONB outbox persistence, due-event locking, query ordering |
| Python unit/API | Shared JWT validation, role denial, deterministic training, RAG parsing/index versioning, citation binding, fixed retrieval quality, abstention, JSON Schema rejection, deterministic replay IDs, bounded producer retries |
| Frontend component/API | Sign-in/session handling, bearer headers, viewer UI, knowledge answer/citation rendering, form validation and failures, queue states, delayed predictions, status updates, modal keyboard behavior, RFC 7807 parsing |
| Compose smoke | Five health checks, real sign-in, role policy, shared Spring/FastAPI token, cited RAG answer and abstention through Nginx, invalid API request, ticket persistence, both Kafka topics, ML result, status update, summary totals |
| Runtime fault injection | Ticket creation during a Kafka outage, durable retry metadata, broker recovery, backend restart, acknowledged relay, and eventual prediction |
| Terraform | Formatting, AzureRM schema validation, and a credential-free mocked plan asserting private PostgreSQL, ingress boundaries, managed ACR access, all event hubs, and a continuously running prediction worker |
| Azure deployment smoke | Manual workflow OIDC login, ACR remote builds, Terraform plan/apply, frontend health, authenticated ticket creation, Event Hubs round trip, and eventual ML classification |
| Kubernetes manifests | Both Kustomize overlays render, source invariants pass, and every built-in resource validates against strict Kubernetes 1.36 schemas |
| Kubernetes runtime | Dedicated kind 1.36 cluster, server-side apply, Restricted Pod Security, all five rollouts, no service-account Secret access, same-origin authenticated event round trip, PostgreSQL pod replacement with ticket persistence, and Redpanda pod replacement with a second event round trip |
| Analytics unit/static | Deterministic 100,000-event cardinality, stable seed digest, valid transition chains, input validation, generator lint, and Power BI TMDL source/measure checks |
| Analytics integration | PostgreSQL 17 operational migrations, bulk lifecycle load, dbt seeds/models, source/generic/singular data tests, SLA consistency, transition integrity, and ticket coverage |
| Observability static/rules | Compose overlay, Collector/Loki/Prometheus/Alertmanager configuration validation, dashboard contract, 30-day SLO records, and fixed `promtool` firing expectations |
| Observability runtime | Prometheus SLI metrics plus OTLP logs/traces for both applications, trace-derived RED metrics, a resolvable W3C Kafka producer-to-consumer span link, Grafana provisioning, AI outage detection, Alertmanager/webhook delivery, recovery, and resolved notification |

## Local commands

Backend:

```bash
cd backend
mvn --batch-mode --no-transfer-progress verify
```

The repository test requires a working Docker engine for Testcontainers.

AI service:

```bash
cd ai-service
python -m pip install -e ".[dev]"
python -m ruff check src tests ../scripts/cloud_smoke_test.py \
  ../scripts/observability_smoke_test.py ../scripts/validate_observability.py \
  ../scripts/kubernetes_smoke_test.py ../scripts/validate_kubernetes.py
python -m pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Full stack:

```bash
docker compose config --quiet
docker compose up --build --detach --wait
python scripts/smoke_test.py
docker compose down --volumes
```

Azure Terraform (no credentials or resources required):

```bash
terraform -chdir=infra/azure fmt -check -recursive
terraform -chdir=infra/azure init -backend=false
terraform -chdir=infra/azure validate
terraform -chdir=infra/azure test
```

The manual Azure workflow performs the credentialed plan/apply and runs
`scripts/cloud_smoke_test.py`. It is intentionally excluded from pull-request CI because it
creates billable resources and requires an explicitly authorized Azure subscription.

Analytics:

```bash
cd analytics
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts
python -m pytest
python scripts/validate_power_bi_model.py
serviceops-generate-analytics
dbt build --project-dir dbt --profiles-dir dbt
```

The final two commands require a migrated PostgreSQL database and the documented
`ANALYTICS_DATABASE_URL`/`DBT_POSTGRES_*` variables. CI supplies an isolated PostgreSQL 17
service, loads all 100,000 events, and runs the complete build rather than compiling SQL
without executing it.

Observability:

```bash
python scripts/validate_observability.py
docker compose -f compose.yaml -f compose.observability.yaml config --quiet
docker compose -p serviceops-observability-verify \
  -f compose.yaml -f compose.observability.yaml up --build --detach --wait
python scripts/smoke_test.py
python scripts/observability_smoke_test.py \
  --exercise-alert --project-name serviceops-observability-verify
```

The full drill intentionally stops and restores only `ai-service`; it does not delete
application or telemetry volumes. The CI observability job validates configuration schemas
and alert behavior without starting the complete stack.

## Baseline acceptance

Before the final baseline commit:

1. Run all three language quality suites.
2. Validate and build the Compose model.
3. Start all five services and require `healthy` state.
4. Run the smoke test and inspect both Kafka topics plus PostgreSQL records.
5. Stop Kafka, create a ticket, and verify its unpublished outbox state and retry metadata.
6. Restart the backend while the row is pending, restore Kafka, and require acknowledged
   publication plus eventual prediction without manual repair.
7. Restart PostgreSQL and the backend without deleting volumes, then re-read the ticket.
8. Tear down with volumes and repeat the full build, start, health, and smoke flow.
9. Tear down with volumes and repeat a second time from clean application data.
10. Inspect every changed and untracked path for secrets and generated artifacts.
11. Generate the deterministic 100,000-event fixture in an isolated database and require a
    green `dbt build`, including all source, generic, and singular tests.
12. Validate that the Power BI semantic model references the tested marts and contains all
    six required business measures without embedded credentials.
13. Run the fixed RAG evaluation, require at least 90% retrieval recall within the top three,
    require every unrelated question to abstain, and exercise a cited answer through Nginx.
14. Validate the observability configurations with their pinned binaries and require the
    `promtool` SLO/availability alert fixtures to pass.
15. Run the telemetry smoke test, then the component-down drill; require both applications'
    metrics, logs, and traces, a resolvable Kafka span link, the provisioned dashboard/data
    sources, firing delivery, application recovery, and a resolved notification.
16. Render both Kubernetes overlays, run strict Kubernetes 1.36 schema checks, and execute
    the disposable kind acceptance test including PostgreSQL and Redpanda pod replacement.

GitHub Actions mirrors the language and Terraform commands and builds every Compose image
after all quality jobs pass. Pull requests require no repository secrets. Azure deploy and
destroy are separate manual actions guarded by OIDC and an exact destroy confirmation.
Kubernetes deploy and destroy are separate manual actions guarded by environment-scoped
cluster/registry credentials and an exact destroy confirmation.

## Intentional exclusions

The baseline does not claim browser-engine end-to-end automation, application load metrics,
security scanning, production model accuracy, cloud availability, or an HA telemetry backend.
Playwright, performance, security, managed observability, multi-cluster failover, and highly
available stateful Kubernetes dependencies remain deployment or roadmap work.
Power BI Desktop/Fabric refresh and visual QA remain environment-specific manual checks;
CI validates the tracked semantic-model structure and its mart contract.
