# Kubernetes deployment

The Kubernetes layer deploys the same five-service runtime as Docker Compose: the public
Nginx frontend, Spring Boot API, FastAPI inference and knowledge service, PostgreSQL, and a
single-node Redpanda broker. Kustomize keeps the shared workload definitions in `base` and
provides two explicit operating profiles:

- `overlays/local` is a resource-bounded, self-contained verification environment. It
  generates documented development credentials and is intended only for an isolated kind
  cluster.
- `overlays/production` uses replicated stateless workloads, CPU autoscaling, a public
  `LoadBalancer` Service, and externally created runtime and registry Secrets. It never
  renders credentials into source-controlled manifests.

The manifests target Kubernetes 1.34 through 1.36 and are schema-checked against 1.36.
The checked kind configuration pins Kubernetes 1.36.1 by digest because that is the image
published with kind 0.32.0. The workload uses stable built-in APIs only; it does not require
Helm, an operator, or custom resource definitions.

## Security and reliability controls

Both overlays enforce the Kubernetes Restricted Pod Security Standard. Every workload runs
as a numeric non-root identity, drops Linux capabilities, blocks privilege escalation, uses
the runtime-default seccomp profile, declares compute requests and limits, and disables
automatic service-account token mounts. Service accounts have no RBAC grants. The frontend
image listens on unprivileged port `8080` and runs as the Nginx user in Compose, Azure, and
Kubernetes.

Startup, readiness, and liveness probes cover all five workloads. PostgreSQL and Redpanda
run as StatefulSets with `ReadWriteOnce` claims; stateless services use rolling Deployments,
topology spreading, and disruption budgets. The production overlay adds `autoscaling/v2`
HPAs for all three stateless services. NetworkPolicies default-deny ingress and allow only
the application paths shown in the architecture. Enforcement requires a CNI that implements
NetworkPolicy.

The AI model volume is deliberately ephemeral in Kubernetes. Each AI pod reproducibly
rebuilds the small bundled model when scheduled, which keeps inference pods independently
scalable. PostgreSQL and Redpanda state is persistent.

## Full local verification with kind

Requirements:

- Docker Desktop with at least 4 GB assigned to its Linux engine;
- Python 3.12+;
- kubectl 1.34+;
- kind 0.32.0;
- Node.js 22+ and the frontend packages for the browser gate.

The verification script refuses to touch a cluster with its chosen name. It builds the
three application images, creates a dedicated kind cluster, loads the images, applies the
local overlay, waits for every rollout, checks that the backend service account cannot read
Secrets, and runs the authenticated public API smoke test through a frontend port-forward.
Quality-gate mode then runs Playwright against the rendered UI and k6 against the same Nginx
boundary. It finally restarts PostgreSQL, proves the classified ticket survived its pod
replacement, restarts Redpanda, and proves a second event round trip. The dedicated cluster
is deleted in `finally` unless `--keep-cluster` is explicitly supplied.

```bash
python scripts/validate_kubernetes.py
cd frontend
npm ci
npx playwright install chromium firefox webkit
cd ..
python scripts/kubernetes_smoke_test.py --quality-gates
```

The Playwright suite checks invalid-login isolation, viewer read-only behavior plus cited
knowledge rendering, and an operator's create/classify/resolve journey on Chromium, Firefox,
and WebKit. `--playwright-channel msedge` intentionally replaces that default matrix with a
single locally installed Chromium channel for targeted diagnosis. Reports are written below
`frontend/playwright-report` and `frontend/test-results`.

The k6 baseline schedules one iteration per second for 30 seconds. Each iteration checks
frontend health, the authenticated ticket queue, and a grounded knowledge response. It
requires fewer than 1% failed requests and p95 latency below 500 ms for health, 1,000 ms for
tickets, and 2,000 ms for knowledge. If `k6` is absent, the script runs a digest-pinned k6
container. The JSON result is written to `performance/results/kubernetes-load-summary.json`.
These thresholds detect regressions in the small kind topology; they are not throughput,
stress, soak, or production-capacity evidence.

On Windows, the scripts also discover `kind.exe` and `kubectl.exe` under
`.tools/kubernetes`. To retain a failed cluster for diagnosis:

```bash
python scripts/kubernetes_smoke_test.py --keep-cluster
kubectl --context kind-serviceops-kubernetes-verify \
  --namespace serviceops-local get pods,pvc,events
```

Delete that retained, dedicated cluster when finished:

```bash
kind delete cluster --name serviceops-kubernetes-verify
```

For manual local access after applying the overlay, forward only the frontend boundary:

```bash
kubectl --namespace serviceops-local port-forward service/frontend 3000:8080
```

Then open <http://localhost:3000>. The local credentials are the same deliberately unsafe
development defaults documented for Compose.

## Deploy to an existing cluster

The `Kubernetes deployment` GitHub Actions workflow is manual and restricted to `main`. It
builds commit-addressed images in GHCR, connects with an environment-scoped kubeconfig,
creates the runtime and image-pull Secrets without writing them to a file, server-validates
the fully rendered resources, applies them, waits for all rollouts, and exercises the public
frontend boundary. A separately confirmed `destroy` action removes only the selected
`serviceops-<environment>` namespace; registry images remain available.

Create a GitHub Environment named `kubernetes-<environment>` and configure these encrypted
secrets:

| Secret | Purpose |
| --- | --- |
| `KUBE_CONFIG_DATA` | Base64-encoded, least-privilege kubeconfig for the target cluster |
| `POSTGRES_PASSWORD` | PostgreSQL and Spring datasource password |
| `JWT_SIGNING_KEY` | Shared signing key, at least 32 characters |
| `OPERATOR_PASSWORD` | Bootstrap operator password, at least 12 characters |
| `VIEWER_PASSWORD` | Bootstrap viewer password, at least 12 characters |
| `REGISTRY_USERNAME` | GHCR identity with package read access |
| `REGISTRY_PASSWORD` | Long-lived GHCR token with package read access |

The workflow identity needs namespace-scoped rights to manage the rendered resources and
Secrets plus permission to create/delete the environment namespace. Review and narrow that
identity for the target cluster. The registry credential must remain valid for later pod
rescheduling; the workflow's short-lived `GITHUB_TOKEN` is used only to publish images.

Before a manual deployment, the cluster must provide:

- a default `ReadWriteOnce` StorageClass with enough capacity for two 2 GiB claims;
- a LoadBalancer implementation or a deliberate patch to the frontend Service;
- metrics-server for HPA CPU metrics;
- a NetworkPolicy-capable CNI if policy enforcement is required;
- at least two schedulable worker nodes to obtain useful replica spreading;
- an external TLS endpoint in front of the LoadBalancer for non-development traffic;
- approved backup, retention, capacity, and disaster-recovery controls for stateful data.

To render the production overlay without deploying it:

```bash
kubectl kustomize k8s/overlays/production > serviceops-kubernetes.yaml
kubeconform -strict -kubernetes-version 1.36.0 serviceops-kubernetes.yaml
```

Before direct use outside the workflow, replace the three GHCR image names/tags in a private
overlay, create `serviceops-runtime` and `serviceops-registry` Secrets in the target
namespace, and run a server-side dry run. Do not commit generated Secret YAML or kubeconfig
material.

## Observability integration

The backend and AI pods carry Prometheus scrape annotations. A scraper in the ServiceOps
namespace needs label `serviceops.io/metrics-scraper=true`; a scraper in another namespace
also needs that pod label and namespace label `serviceops.io/observability=true`. To export
OTLP telemetry to a cluster collector, patch `OTEL_SDK_DISABLED=false` and the approved OTLP
endpoint/protocol into the application Deployments. The repository's checked single-node
Compose telemetry stack is not silently installed into arbitrary clusters.

## Scope and production boundaries

This implementation proves a reproducible Kubernetes deployment and recovery path; it is not
a blanket production-readiness claim. The bundled PostgreSQL and Redpanda StatefulSets each
have one replica, so they remain single points of availability. A production platform team
should normally replace them with backed-up, replicated managed services or an approved
operator-based design. The manifests do not install a cloud load balancer, certificate
issuer, DNS controller, storage driver, CNI, metrics-server, secret manager, or multi-cluster
failover system because those are cluster-level choices, not safe application placeholders.

The checked browser and load paths likewise establish a reproducible acceptance baseline, not
an operating-system, device, browser-version, or multi-node availability/load claim. Security
automation is documented in `docs/security-testing.md`; automated findings must still be
interpreted in the target environment and do not replace an approved security assessment.
