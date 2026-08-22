---
id: access-vpn-connectivity
title: VPN connectivity recovery
revision: 2026-08-22
---
# VPN connectivity recovery

## Establish scope
Record the affected user, managed device identifier, operating system, approved VPN client version, gateway or region, first failure time in UTC, and exact sanitized error. Confirm whether normal internet access works and whether one user, one site, or several users are affected. Keep exported profiles, certificates, authentication codes, and private addresses out of shared ticket notes.

## Recover safely
Check the service-status channel, device clock, recent network changes, and whether the approved profile is current. Have the user reconnect once from a known network and complete the normal multi-factor flow. Collect the approved client diagnostic bundle after redaction when the failure continues. Do not disable endpoint protection, the host firewall, certificate validation, or multi-factor authentication to force a connection.

## Escalation conditions
Escalate to the network or identity owner when multiple users cannot reach the same gateway, the client reports an invalid gateway certificate, conditional-access evaluation fails unexpectedly, or a valid tunnel cannot reach required internal services. Include the sanitized error, timestamps, gateway, device and client versions, network type, and every reversible check already completed.
