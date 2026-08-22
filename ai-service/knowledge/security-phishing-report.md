---
id: security-phishing-report
title: Suspicious email and phishing response
revision: 2026-08-22
---
# Suspicious email and phishing response

## Contain the report
Ask whether the recipient opened an attachment, followed a link, approved a sign-in, entered account details, or ran downloaded content. Use the approved reporting mechanism so the original message remains available for analysis; do not forward active links or attachments through ordinary email or ticket comments. Follow the security response playbook before isolating a managed device or changing account state.

## Preserve evidence
Capture the message identifier, received time in UTC, sender and reply-to domains, recipient scope, subject fragment, and the reporting tool reference. Preserve full headers and attachment hashes only in the restricted evidence location. Represent suspicious destinations as non-clickable text and minimize copied message content so personal or customer data is not spread into general support records.

## Escalation conditions
Escalate immediately to the security team when account details were entered, a sign-in or consent prompt was approved, content executed, endpoint protection alerted, or the message reached multiple recipients. Link the identity and endpoint response records, affected accounts or devices, known indicators, and containment already authorized. Account recovery must use the approved identity workflow rather than instructions contained in the reported message.
