#!/usr/bin/env python3
"""Build and verify ServiceOps in an isolated kind cluster."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "serviceops-local"
KIND_NODE_IMAGE = (
    "kindest/node:v1.36.1@sha256:"
    "3489c7674813ba5d8b1a9977baea8a6e553784dab7b84759d1014dbd78f7ebd5"
)
K6_IMAGE = "grafana/k6@sha256:a33a0cfdc4d2483d6b7a3a22e726a499ff2831a671a49239104cd34a9937523c"
TICKET_PATTERN = re.compile(r"ticket ([0-9a-f-]{36}) classified")


def executable(name: str, override: str | None) -> str:
    if override:
        return override
    found = shutil.which(name)
    if found:
        return found
    local = ROOT / ".tools" / "kubernetes" / f"{name}.exe"
    if local.is_file():
        return str(local)
    raise RuntimeError(f"{name} is required; set --{name} or add it to PATH")


def run(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> str:
    print("+", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        capture_output=capture,
        text=True,
        env=env,
    )
    if capture and completed.stdout:
        print(completed.stdout, end="")
    return completed.stdout if capture else ""


def kubectl(
    command: str,
    context: str,
    *arguments: str,
    capture: bool = False,
    check: bool = True,
) -> str:
    return run(
        [command, "--context", context, *arguments], capture=capture, check=check
    )


def request(path: str, *, token: str | None = None, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    http_request = urllib.request.Request(
        f"http://127.0.0.1:3000{path}",
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(http_request, timeout=10) as response:
        body = response.read()
        if response.headers.get_content_type() == "application/json":
            return json.loads(body)
        return body


def wait_for_frontend(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if request("/health") == b"UP":
                return
        except OSError:
            pass
        time.sleep(2)
    raise TimeoutError("Frontend port-forward did not become ready")


def run_public_smoke() -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "SERVICEOPS_BASE_URL": "http://localhost:3000",
            "SERVICEOPS_OPERATOR_USERNAME": "operator",
            "SERVICEOPS_OPERATOR_PASSWORD": "operator_dev_2026",
        }
    )
    output = run(
        [sys.executable, str(ROOT / "scripts" / "cloud_smoke_test.py")],
        capture=True,
        env=environment,
    )
    match = TICKET_PATTERN.search(output)
    if not match:
        raise AssertionError("Could not recover the created ticket id from the smoke output")
    return match.group(1)


def run_browser_acceptance(
    *,
    npm_override: str | None,
    node_override: str | None,
    channel: str | None,
) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "SERVICEOPS_BASE_URL": "http://localhost:3000",
            "SERVICEOPS_OPERATOR_USERNAME": "operator",
            "SERVICEOPS_OPERATOR_PASSWORD": "operator_dev_2026",
            "SERVICEOPS_VIEWER_USERNAME": "viewer",
            "SERVICEOPS_VIEWER_PASSWORD": "viewer_dev_2026",
        }
    )
    if channel:
        environment["PLAYWRIGHT_CHANNEL"] = channel

    if node_override:
        playwright_cli = ROOT / "frontend" / "node_modules" / "@playwright" / "test" / "cli.js"
        if not playwright_cli.is_file():
            raise RuntimeError(
                "Playwright dependencies are missing; install frontend packages before using --node"
            )
        command = [
            node_override,
            str(playwright_cli),
            "test",
            "--config",
            str(ROOT / "frontend" / "playwright.config.ts"),
        ]
    else:
        npm = executable("npm", npm_override)
        command = [npm, "--prefix", str(ROOT / "frontend"), "run", "test:e2e"]
    run(command, env=environment)


def run_load_acceptance(*, docker: str, k6_override: str | None) -> None:
    results = ROOT / "performance" / "results"
    results.mkdir(parents=True, exist_ok=True)
    script = ROOT / "performance" / "kubernetes-load.js"
    summary = results / "kubernetes-load-summary.json"

    k6 = k6_override or shutil.which("k6")
    if k6:
        environment = os.environ.copy()
        environment.update(
            {
                "SERVICEOPS_BASE_URL": "http://127.0.0.1:3000",
                "SERVICEOPS_OPERATOR_USERNAME": "operator",
                "SERVICEOPS_OPERATOR_PASSWORD": "operator_dev_2026",
                "K6_SUMMARY_PATH": str(summary),
            }
        )
        run([k6, "run", str(script)], env=environment)
        return

    base_url = (
        "http://127.0.0.1:3000"
        if sys.platform.startswith("linux")
        else "http://host.docker.internal:3000"
    )
    command = [docker, "run", "--rm"]
    if sys.platform.startswith("linux"):
        command.extend(["--network", "host"])
    command.extend(
        [
            "--env",
            f"SERVICEOPS_BASE_URL={base_url}",
            "--env",
            "SERVICEOPS_OPERATOR_USERNAME=operator",
            "--env",
            "SERVICEOPS_OPERATOR_PASSWORD=operator_dev_2026",
            "--env",
            "K6_SUMMARY_PATH=/workspace/performance/results/kubernetes-load-summary.json",
            "--volume",
            f"{ROOT}:/workspace",
            "--workdir",
            "/workspace",
            K6_IMAGE,
            "run",
            "performance/kubernetes-load.js",
        ]
    )
    run(command)


def assert_ticket_persisted(ticket_id: str, timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            login = request(
                "/api/auth/login",
                payload={"username": "operator", "password": "operator_dev_2026"},
            )
            ticket = request(f"/api/tickets/{ticket_id}", token=login["accessToken"])
            if ticket["id"] == ticket_id and ticket["predictedCategory"]:
                return
            last_error = AssertionError("The restored ticket is not classified")
        except (OSError, KeyError) as error:
            last_error = error
        time.sleep(2)
    raise TimeoutError(
        "The classified ticket was not readable after the PostgreSQL restart"
    ) from last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster-name", default="serviceops-kubernetes-verify")
    parser.add_argument("--docker")
    parser.add_argument("--kubectl")
    parser.add_argument("--kind")
    parser.add_argument("--npm")
    parser.add_argument("--node")
    parser.add_argument("--playwright-channel")
    parser.add_argument("--k6")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--quality-gates", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep-cluster", action="store_true")
    parser.add_argument("--skip-recovery", action="store_true")
    args = parser.parse_args()

    docker = executable("docker", args.docker)
    kubectl_command = executable("kubectl", args.kubectl)
    kind = executable("kind", args.kind)
    context = f"kind-{args.cluster_name}"
    existing = run([kind, "get", "clusters"], capture=True).splitlines()
    if args.cluster_name in existing:
        raise RuntimeError(
            f"Refusing to alter existing kind cluster {args.cluster_name!r}; choose another name"
        )

    cluster_created = False
    port_forward: subprocess.Popen[bytes] | None = None
    try:
        if not args.skip_build:
            run([docker, "build", "-t", "serviceops-backend:kubernetes-local", "backend"])
            run(
                [
                    docker,
                    "build",
                    "-t",
                    "serviceops-ai:kubernetes-local",
                    "-f",
                    "ai-service/Dockerfile",
                    ".",
                ]
            )
            run([docker, "build", "-t", "serviceops-frontend:kubernetes-local", "frontend"])

        run(
            [
                kind,
                "create",
                "cluster",
                "--name",
                args.cluster_name,
                "--image",
                KIND_NODE_IMAGE,
                "--config",
                str(ROOT / "k8s" / "kind-config.yaml"),
                "--wait",
                "180s",
            ]
        )
        cluster_created = True
        for image in (
            "serviceops-backend:kubernetes-local",
            "serviceops-ai:kubernetes-local",
            "serviceops-frontend:kubernetes-local",
        ):
            run([kind, "load", "docker-image", image, "--name", args.cluster_name])

        kubectl(
            kubectl_command,
            context,
            "apply",
            "--server-side",
            "--field-manager=serviceops-verification",
            "-k",
            str(ROOT / "k8s" / "overlays" / "local"),
        )
        for workload in ("statefulset/postgres", "statefulset/kafka"):
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "rollout",
                "status",
                workload,
                "--timeout=360s",
            )
        for workload in ("deployment/backend", "deployment/ai-service", "deployment/frontend"):
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "rollout",
                "status",
                workload,
                "--timeout=360s",
            )

        denied = kubectl(
            kubectl_command,
            context,
            "auth",
            "can-i",
            "get",
            "secrets",
            "--as=system:serviceaccount:serviceops-local:backend",
            "-n",
            NAMESPACE,
            capture=True,
            check=False,
        ).strip()
        if denied != "no":
            raise AssertionError("The backend ServiceAccount unexpectedly has Secret read access")

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        port_forward = subprocess.Popen(
            [
                kubectl_command,
                "--context",
                context,
                "-n",
                NAMESPACE,
                "port-forward",
                "service/frontend",
                "3000:8080",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        wait_for_frontend()
        ticket_id = run_public_smoke()

        if args.browser or args.quality_gates:
            run_browser_acceptance(
                npm_override=args.npm,
                node_override=args.node,
                channel=args.playwright_channel,
            )
        if args.load or args.quality_gates:
            run_load_acceptance(docker=docker, k6_override=args.k6)

        if not args.skip_recovery:
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "delete",
                "pod/postgres-0",
                "--wait=true",
                "--timeout=180s",
            )
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "wait",
                "--for=condition=Ready",
                "pod/postgres-0",
                "--timeout=360s",
            )
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "rollout",
                "status",
                "deployment/backend",
                "--timeout=360s",
            )
            assert_ticket_persisted(ticket_id)

            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "delete",
                "pod/kafka-0",
                "--wait=true",
                "--timeout=180s",
            )
            kubectl(
                kubectl_command,
                context,
                "-n",
                NAMESPACE,
                "wait",
                "--for=condition=Ready",
                "pod/kafka-0",
                "--timeout=360s",
            )
            run_public_smoke()

        kubectl(
            kubectl_command,
            context,
            "-n",
            NAMESPACE,
            "get",
            "pods,pvc,service",
            "-o",
            "wide",
        )
        checked = "API flow, RBAC, and persistence"
        if args.quality_gates:
            checked += ", browser automation, and bounded load thresholds"
        print(f"Kubernetes kind deployment, {checked} checks passed.")
        return 0
    finally:
        if port_forward is not None:
            port_forward.terminate()
            try:
                port_forward.wait(timeout=10)
            except subprocess.TimeoutExpired:
                port_forward.kill()
        if cluster_created and not args.keep_cluster:
            run([kind, "delete", "cluster", "--name", args.cluster_name])


if __name__ == "__main__":
    raise SystemExit(main())
