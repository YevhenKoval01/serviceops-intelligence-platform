# Kubernetes load baseline

`kubernetes-load.js` is a small regression profile invoked by
`scripts/kubernetes_smoke_test.py --quality-gates`. It authenticates once, schedules one
iteration per second for 30 seconds, and makes three requests per iteration through the
kind-hosted frontend: health, the ticket queue, and a grounded knowledge query.

The gate requires content checks above 99%, fewer than 1% failed HTTP requests, and p95
latency below 500 ms for health, 1,000 ms for tickets, and 2,000 ms for knowledge. The
machine-readable summary is written to the ignored `performance/results` directory and is
uploaded by CI.

This intentionally low-rate run is suitable for catching large local regressions on a
shared CI runner. It is not a concurrency ceiling, capacity plan, stress test, soak test, or
production service-level claim.
