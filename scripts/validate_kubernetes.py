#!/usr/bin/env python3
"""Validate ServiceOps Kubernetes source and rendered Kustomize contracts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KUBERNETES = ROOT / "k8s"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def render(kubectl: str, overlay: str) -> str:
    completed = subprocess.run(
        [kubectl, "kustomize", str(KUBERNETES / "overlays" / overlay)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def validate_sources() -> None:
    required_files = {
        "base/kustomization.yaml",
        "base/serviceaccounts.yaml",
        "base/configmap.yaml",
        "base/postgres.yaml",
        "base/kafka.yaml",
        "base/backend.yaml",
        "base/ai-service.yaml",
        "base/frontend.yaml",
        "base/network-policies.yaml",
        "base/pod-disruption-budgets.yaml",
        "overlays/local/kustomization.yaml",
        "overlays/local/namespace.yaml",
        "overlays/production/kustomization.yaml",
        "overlays/production/namespace.yaml",
        "overlays/production/horizontal-pod-autoscalers.yaml",
        "kind-config.yaml",
        "README.md",
    }
    missing = sorted(path for path in required_files if not (KUBERNETES / path).is_file())
    require(not missing, f"Missing Kubernetes files: {', '.join(missing)}")

    base_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((KUBERNETES / "base").glob("*.yaml"))
    )
    production_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((KUBERNETES / "overlays" / "production").glob("*.yaml"))
    )
    kind_text = (KUBERNETES / "kind-config.yaml").read_text(encoding="utf-8")

    require("kind: Secret" not in base_text, "Base must not contain plaintext Secrets")
    require(
        "kind: Secret" not in production_text,
        "Production overlay must consume externally created Secrets",
    )
    require(":latest" not in base_text + production_text, "Container tags must be pinned")
    require(base_text.count("kind: Deployment") == 3, "Expected three application Deployments")
    require(base_text.count("kind: StatefulSet") == 2, "Expected two stateful dependencies")
    require(
        base_text.count("automountServiceAccountToken: false") >= 10,
        "Every ServiceAccount and Pod must disable API token mounting",
    )
    require(
        base_text.count("allowPrivilegeEscalation: false") >= 7,
        "Every container and init container must block privilege escalation",
    )
    for probe in ("startupProbe:", "readinessProbe:", "livenessProbe:"):
        require(base_text.count(probe) == 5, f"Every workload must define {probe}")
    require(
        base_text.count("resources:") >= 10,
        "Containers and persistent claims must declare resource requirements",
    )
    require("kind: NetworkPolicy" in base_text, "Network isolation policy is required")
    require("kind: PodDisruptionBudget" in base_text, "Disruption budgets are required")
    require(
        production_text.count("kind: HorizontalPodAutoscaler") == 3,
        "Production overlay must autoscale all stateless applications",
    )
    require("type: LoadBalancer" in production_text, "Production frontend must be exposed")
    require("kind: Cluster" in kind_text, "The reproducible kind cluster config is missing")


def validate_rendered(local: str, production: str) -> None:
    def kind_count(rendered: str, kind: str) -> int:
        return sum(line == f"kind: {kind}" for line in rendered.splitlines())

    require("namespace: serviceops-local" in local, "Local resources must be namespace scoped")
    require("name: serviceops-local" in local, "Local Namespace was not rendered")
    require(kind_count(local, "Secret") == 1, "Local overlay must generate one dev Secret")
    require(
        "credential-scope: isolated-local-development-only" in local,
        "Dev Secret warning missing",
    )
    require("namespace: serviceops" in production, "Production resources must be namespace scoped")
    require(kind_count(production, "Secret") == 0, "Production render must not embed credentials")
    require(
        "ghcr.io/yevhenkoval01/serviceops-backend:main" in production,
        "Production backend image customization failed",
    )
    require(
        production.count("imagePullSecrets:") == 3,
        "Private registry credentials must cover each application Deployment",
    )
    require(
        production.count("replicas: 2") == 3,
        "Production must start every stateless application with two replicas",
    )
    require(
        production.count("minReplicas: 2") == 3,
        "Production HPAs must preserve two replicas of every stateless application",
    )
    for rendered, name in ((local, "local"), (production, "production")):
        require(":latest" not in rendered, f"{name} render contains an unpinned latest tag")
        require(kind_count(rendered, "Deployment") == 3, f"{name} render lost a Deployment")
        require(kind_count(rendered, "StatefulSet") == 2, f"{name} render lost a StatefulSet")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kubectl", help="kubectl executable used for Kustomize rendering")
    args = parser.parse_args()
    kubectl = args.kubectl or shutil.which("kubectl")
    if not kubectl:
        raise RuntimeError("kubectl is required to render and validate the overlays")

    validate_sources()
    validate_rendered(render(kubectl, "local"), render(kubectl, "production"))
    print("Kubernetes source and Kustomize render contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
