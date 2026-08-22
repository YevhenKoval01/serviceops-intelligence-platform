---
id: collaboration-email-delivery
title: Email delivery investigation
revision: 2026-08-22
---
# Email delivery investigation

## Trace the message
Confirm the sender and recipient domains, send time in UTC, subject fragment, message identifier, delivery or non-delivery status, and whether one or many recipients are affected. Use message tracing rather than requesting an entire mailbox export. Keep message bodies, recipient lists, and attachments out of general ticket notes unless a restricted evidence process explicitly requires them.

## Interpret the result
Distinguish accepted, queued, deferred, bounced, quarantined, and delivered states. Record the enhanced status code and destination response when available. Follow the documented retry interval for a temporary deferral and check approved quarantine controls with the recipient. Avoid repeated manual resends because they can create duplicates, worsen rate limits, and obscure the original trace.

## Escalation conditions
Escalate to messaging operations when the outbound queue continues to grow, several destination domains fail, authentication or reputation checks regress, a message has no trace despite a valid identifier, or a time-critical communication remains deferred past its operational deadline. Include the trace identifier, timestamps, affected domains, status codes, queue trend, and any safe retry already observed.
