# Security testing

The `Security` GitHub Actions workflow runs for changes to `main`, pull requests, and every
Tuesday. It keeps analysis separate from deployment credentials and uses read-only repository
permissions except for the CodeQL job's required `security-events: write` permission.

## Checked controls

- CodeQL runs extended queries for Java/Kotlin, JavaScript/TypeScript, Python, and GitHub
  Actions and publishes results to code scanning.
- Trivy rejects fixed high or critical vulnerabilities in Maven and npm dependency manifests.
  CI exports the pinned Python runtime and development declarations from each tracked
  `pyproject.toml` to scanner-compatible temporary requirements manifests first.
- Trivy scans explicitly listed tracked source, infrastructure, test, and workflow paths for
  secrets so ignored package/download caches are not traversed or uploaded.
- Dockerfiles, Terraform, and both fully rendered Kubernetes overlays reject high or critical
  configuration findings.
- The four application images and pinned PostgreSQL and Redpanda images reject fixed critical
  runtime vulnerabilities, covering installed transitive packages as well as direct project
  dependencies. A CycloneDX JSON SBOM is retained for each image for 30 days.

The PostgreSQL 17.10 image has one scoped, time-bounded exception for `CVE-2025-68121` in
`gosu`'s statically linked Go TLS code. In this platform `gosu` only performs a local uid/gid
transition and never opens a TLS connection, so the vulnerable path is unreachable. Platform
engineering owns the exception and must upgrade or re-review it by 2026-09-30. The exception
file is supplied only while scanning the PostgreSQL image; all other scans remain unaffected.

Trivy is downloaded directly from its pinned release and verified with the publisher's
checksum. The workflow deliberately does not execute a mutable third-party scanning action.
GitHub-owned actions are pinned to full commit identifiers in the new gates.

## Triage and boundaries

A failed gate is evidence to investigate, not permission to suppress a finding broadly.
Prefer upgrading or hardening the exact affected component. If a false positive or accepted
risk requires an exception, document its identifier, affected asset, owner, expiry, and
review rationale in the same change; do not add an unbounded ignore.

The runtime image gate currently blocks fixed critical findings, while source dependencies
and configuration block fixed high and critical findings. This accounts for upstream base
image packages while keeping an unambiguous release blocker. Teams deploying into a target
environment should strengthen the image policy to their approved risk standard.

Automated static and vulnerability scanners do not prove the absence of vulnerabilities.
Threat modeling, penetration testing, dynamic application testing, credential/identity
review, supply-chain governance, and environment-specific policy enforcement remain required
for a production security assessment.
