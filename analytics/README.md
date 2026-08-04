# ServiceOps analytics

This directory contains the complete local analytics path:

1. Spring Boot writes an immutable `ticket_lifecycle_events` record for ticket creation
   and every real status transition.
2. The deterministic fixture generator can add exactly 100,000 non-sensitive lifecycle
   events for realistic analytical validation.
3. dbt builds tested PostgreSQL staging, lifecycle, performance, calendar, and daily trend
   models in the `analytics_*` schemas.
4. The source-controlled Power BI TMDL semantic model imports the marts and supplies the
   required operational measures.

Normal `docker compose up` does not execute analytics or add fixture data. The analytics
service is behind the opt-in `analytics` profile.

## Build the analytical dataset

Start the normal stack so Flyway applies migration V4, then run the generator and dbt:

```bash
docker compose up --build --detach --wait
docker compose --profile analytics build analytics
docker compose --profile analytics run --rm analytics serviceops-generate-analytics
docker compose --profile analytics run --rm analytics
```

The default generator uses seed `20260804`, a fixed UTC anchor, 40,000 tickets, and
100,000 lifecycle events. UUIDv5 identifiers and a printed SHA-256 digest make the output
reproducible. Inserts use `ON CONFLICT DO NOTHING`, so rerunning the same fixture is
idempotent. Use a dedicated Compose project/volume when the synthetic tickets should not
appear in a developer's normal operator queue.

Useful overrides:

```bash
serviceops-generate-analytics --event-count 100000 --seed 20260804 \
  --anchor 2026-07-31T00:00:00Z
dbt build --project-dir analytics/dbt --profiles-dir analytics/dbt
```

Without `ANALYTICS_DATABASE_URL`, the generator only constructs and summarizes the data;
it does not connect to PostgreSQL. dbt connection values come from the `DBT_POSTGRES_*`
environment variables documented in `dbt/profiles.yml`.

## Metric definitions

| Metric | Definition |
| --- | --- |
| SLA compliance | Resolved tickets whose latest applicable resolution occurred on or before the priority-based resolution deadline, divided by resolved tickets with a measurable resolution. |
| Backlog age | Current time minus creation time for tickets not currently resolved. |
| First response time | Creation to the first exact transition away from `OPEN`; migrated snapshots use `updated_at` and are labeled accordingly. |
| MTTR | Creation to the latest resolution for tickets currently resolved. |
| Reopen rate | Tickets with at least one `RESOLVED`-to-active transition divided by all tickets in filter context. |
| Category trend | Ticket creation volume by category and calendar context, with a Power BI month-over-month measure. |

The tracked SLA reference values are 60/240 minutes for `HIGH`, 240/480 for `MEDIUM`,
and 480/1440 for `LOW` first response/resolution. They are analytical policy assumptions,
not an operational escalation engine.

Migration V4 cannot reconstruct transitions that occurred before history retention
existed. It therefore writes a `MIGRATED` snapshot and the marts expose
`history_quality = 'MIGRATED_SNAPSHOT'`; new and generated histories are marked `EXACT`.

## Development checks

```bash
cd analytics
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts
python -m pytest
python scripts/validate_power_bi_model.py
```

The authoritative end-to-end analytics gate uses PostgreSQL 17, applies the operational
migrations, loads all 100,000 events, and runs `dbt build` so both models and data tests
execute against the real database.
