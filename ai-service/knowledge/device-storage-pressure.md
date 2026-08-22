---
id: device-storage-pressure
title: Managed device storage pressure
revision: 2026-08-22
---
# Managed device storage pressure

## Confirm the pressure
Record the managed device identifier, operating system, affected volume, total and free capacity, when the warning began, and whether applications or updates are failing. Use the approved inventory or storage view to identify broad usage categories. Do not collect filenames or user content unless the data owner authorizes a specific diagnostic need.

## Recover safely
Apply the supported cleanup workflow for temporary files, approved application caches, and expired update packages. Respect log-retention, legal-hold, backup, and records-management requirements. Do not remove audit data, system components, recovery partitions, or user files merely to clear an alert. Re-measure free capacity and the failed workflow after cleanup instead of relying on the cleanup tool's reported total.

## Escalation conditions
Escalate to endpoint engineering when free space remains below the managed-device threshold, usage grows unexpectedly after cleanup, encryption or filesystem checks report a fault, the drive reports hardware-health warnings, or the same pattern affects several devices. Include capacity measurements, category-level growth, health state, cleanup actions, and whether business work is blocked.
