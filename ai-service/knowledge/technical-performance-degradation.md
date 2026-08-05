---
id: technical-performance-degradation
title: Performance degradation triage
revision: 2026-08-05
---
# Performance degradation triage

## Measure the symptom
Record the affected workflow, region, time window, representative correlation identifiers, and observed latency rather than using only descriptions such as slow. Compare median and tail latency with the normal baseline, and identify whether the delay is in the client, API, database, queue, or an external dependency.

## Reduce risk
Pause nonessential bulk work when it competes with an impacted customer path and the relevant runbook authorizes that action. Do not restart services or scale resources without confirming ownership and recording the reason. Prefer a reversible mitigation, then verify it with the same latency measurement used to establish impact.

## Escalation conditions
Escalate when a critical workflow exceeds its agreed latency objective, timeouts affect multiple customers, or queue depth continues to grow. Provide measurements, the comparison baseline, dependency state, and any reversible mitigation attempted so the receiving team can distinguish capacity pressure from a failing dependency.
