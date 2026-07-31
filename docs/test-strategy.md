# Test strategy

The baseline uses a small test pyramid: deterministic unit tests are the fastest
feedback, focused integration tests cover framework and database behavior, and the
Compose smoke test proves the real cross-service flow.

## Quality layers

| Layer | Coverage |
| --- | --- |
| Java unit and web slice | Request normalization and validation, RFC 7807 errors, ticket/event service behavior, prediction contract validation and idempotency, structured dead-letter records |
| Java repository integration | Real PostgreSQL 17 container, Flyway schema validation, JPA ticket persistence, JSONB event persistence, query ordering |
| Python unit/API | Dataset schema, deterministic training, response constraints, trimmed input validation, JSON Schema rejection, deterministic replay IDs, bounded producer retries |
| Frontend component/API | Form validation and failures, queue and empty states, delayed predictions, status updates, modal keyboard behavior, RFC 7807 parsing |
| Compose smoke | Five health checks, real frontend asset, invalid API request, ticket persistence, both Kafka topics, ML result, queue listing, status update, summary totals |

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
python -m ruff check src tests
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

## Baseline acceptance

Before the final baseline commit:

1. Run all three language quality suites.
2. Validate and build the Compose model.
3. Start all five services and require `healthy` state.
4. Run the smoke test and inspect both Kafka topics plus PostgreSQL records.
5. Restart PostgreSQL and the backend without deleting volumes, then re-read the ticket.
6. Tear down with volumes and repeat the full build, start, health, and smoke flow.
7. Tear down with volumes and repeat a second time from clean application data.
8. Inspect every changed and untracked path for secrets and generated artifacts.

GitHub Actions mirrors the language commands and builds every Compose image after all
quality jobs pass. Pull requests require no repository secrets.

## Intentional exclusions

The baseline does not claim browser-engine end-to-end automation, load metrics, security
scanning, production model accuracy, or cloud reliability. Playwright, performance tests,
and security gates are documented roadmap work.
