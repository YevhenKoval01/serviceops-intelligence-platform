---
id: technical-api-errors
title: API error triage
revision: 2026-08-05
---
# API error triage

## Establish impact
Record the affected endpoint, region, first observed time in UTC, HTTP status, request correlation identifier, and whether retries succeed. Remove credentials, authorization headers, session cookies, and personal data before attaching a request or response. Compare the report with the service status page and recent deployment history.

## Safe diagnostics
Reproduce with a non-production test account and the smallest redacted request that shows the failure. For rate-limit responses, respect the Retry-After value and stop aggressive retries. For server errors, capture one correlation identifier and timestamp, then check service logs and dependency health instead of repeatedly submitting the same mutation.

## Incident escalation
Open an incident when failures affect multiple customers, a critical workflow is unavailable, or the error rate continues to rise. Include impact, start time, affected region and endpoint, one sanitized correlation identifier, and mitigation already attempted. Never invent a recovery estimate; the incident lead owns customer-facing timing updates.
