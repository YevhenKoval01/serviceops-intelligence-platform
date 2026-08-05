---
id: delivery-delayed-order
title: Delayed order response
revision: 2026-08-05
---
# Delayed order response

## Check shipment state
Confirm the order identifier, destination region, carrier, tracking identifier, promised delivery window, and most recent carrier scan. A label-created event without a carrier acceptance scan means the parcel may not yet have entered the carrier network. Avoid publishing a customer's street address or telephone number in shared ticket notes.

## Customer response
Give the customer the latest verified carrier status and a realistic next checkpoint. If the promised window has passed, follow the documented replacement or refund policy for the destination and product type. Record the chosen remedy and carrier case identifier so another operator can continue the work without asking the customer to repeat it.

## Escalation conditions
Escalate to logistics when tracking has not advanced for two business days after carrier acceptance, a temperature-controlled shipment is late, or several orders on the same route are affected. Suspected loss, damage, or theft requires the carrier-claim workflow rather than an unsupported delivery estimate.
