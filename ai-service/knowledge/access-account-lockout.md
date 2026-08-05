---
id: access-account-lockout
title: Account lockout recovery
revision: 2026-08-05
---
# Account lockout recovery

## Confirm the lockout
Verify the affected username and the identity provider shown on the sign-in page. Ask the user for the approximate time of the last successful sign-in, but never ask for their password or authentication code. Check whether the account is disabled, locked after repeated failures, or blocked by a conditional-access rule before changing account state.

## Restore access
For a temporary failed-attempt lockout, wait for the configured lockout interval and have the user retry once in a private browser session. If the account remains locked, an authorized identity administrator must unlock it and issue the approved password-reset flow. Confirm that multi-factor authentication still succeeds after the reset; do not bypass or disable it to close the ticket.

## Escalate safely
Escalate immediately to the identity team when several accounts lock at the same time, an unfamiliar location appears in the audit record, or the user denies making the failed attempts. Preserve the relevant timestamp, username, client address, and correlation identifier without copying passwords, tokens, or authentication codes into the ticket.
