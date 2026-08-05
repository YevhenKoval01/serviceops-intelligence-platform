---
id: billing-duplicate-charge
title: Duplicate charge investigation
revision: 2026-08-05
---
# Duplicate charge investigation

## Validate the report
Confirm the order number, invoice number, charge dates, currencies, and amounts. Determine whether one entry is a temporary authorization hold rather than a settled charge. Never request a complete payment-card number or security code; retain only the approved masked reference supplied by the payment system.

## Investigate and correct
Compare the payment-provider transaction identifiers with the billing ledger and order history. If two settled transactions map to one order, link both identifiers in the restricted billing record and use the approved refund workflow for the duplicate. Do not promise a posting date because the customer's bank controls when a refund becomes visible.

## Escalation conditions
Escalate to payments engineering when multiple customers report duplicate settlements, transaction identifiers are missing, or the ledger and provider disagree. Treat any unexpected exposure of unmasked payment data as a security incident and follow the payment-data incident procedure.
