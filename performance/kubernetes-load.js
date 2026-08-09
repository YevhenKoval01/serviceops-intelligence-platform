import http from "k6/http";
import { check } from "k6";
import { Rate } from "k6/metrics";

const baseUrl = (__ENV.SERVICEOPS_BASE_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const username = __ENV.SERVICEOPS_OPERATOR_USERNAME || "operator";
const password = __ENV.SERVICEOPS_OPERATOR_PASSWORD || "operator_dev_2026";
const contentChecks = new Rate("serviceops_content_checks");

export const options = {
  scenarios: {
    kubernetes_baseline: {
      executor: "constant-arrival-rate",
      rate: 1,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 2,
      maxVUs: 6,
      gracefulStop: "10s",
    },
  },
  thresholds: {
    checks: ["rate>0.99"],
    serviceops_content_checks: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:health}": ["p(95)<500"],
    "http_req_duration{endpoint:tickets}": ["p(95)<1000"],
    "http_req_duration{endpoint:knowledge}": ["p(95)<2000"],
  },
};

const headers = {
  "Content-Type": "application/json",
  "User-Agent": "serviceops-kubernetes-load/1",
};

export function setup() {
  const response = http.post(
    `${baseUrl}/api/auth/login`,
    JSON.stringify({ username, password }),
    { headers, tags: { endpoint: "login" } },
  );
  const accepted = check(response, {
    "load-test login succeeds": (candidate) => candidate.status === 200,
  });
  if (!accepted) {
    throw new Error(`Authentication failed with HTTP ${response.status}`);
  }
  return { token: response.json("accessToken") };
}

export default function ({ token }) {
  const authenticatedHeaders = { ...headers, Authorization: `Bearer ${token}` };

  const health = http.get(`${baseUrl}/health`, { tags: { endpoint: "health" } });
  contentChecks.add(
    check(health, {
      "frontend is healthy": (response) => response.status === 200 && response.body === "UP",
    }),
  );

  const tickets = http.get(`${baseUrl}/api/tickets`, {
    headers: authenticatedHeaders,
    tags: { endpoint: "tickets" },
  });
  contentChecks.add(
    check(tickets, {
      "ticket queue is readable": (response) => response.status === 200 && Array.isArray(response.json()),
    }),
  );

  const knowledge = http.post(
    `${baseUrl}/assistant/ask`,
    JSON.stringify({ question: "What should I capture for repeated HTTP 500 API errors?" }),
    { headers: authenticatedHeaders, tags: { endpoint: "knowledge" } },
  );
  contentChecks.add(
    check(knowledge, {
      "knowledge answer is grounded": (response) =>
        response.status === 200 &&
        response.json("grounded") === true &&
        response.json("citations.0.documentId") === "technical-api-errors",
    }),
  );
}

export function handleSummary(data) {
  const selected = [
    "http_reqs",
    "http_req_failed",
    "http_req_duration",
    "http_req_duration{endpoint:health}",
    "http_req_duration{endpoint:tickets}",
    "http_req_duration{endpoint:knowledge}",
    "checks",
    "serviceops_content_checks",
    "vus_max",
    "iterations",
  ];
  const metrics = Object.fromEntries(
    selected.filter((name) => data.metrics[name]).map((name) => [name, data.metrics[name].values]),
  );
  const summary = {
    generatedAt: new Date().toISOString(),
    profile: "1 iteration/second for 30 seconds; three HTTP requests per iteration",
    thresholdsPassed: Object.values(data.metrics).every(
      (metric) => !metric.thresholds || Object.values(metric.thresholds).every((result) => result.ok),
    ),
    metrics,
  };
  const rendered = `${JSON.stringify(summary, null, 2)}\n`;
  const outputPath = __ENV.K6_SUMMARY_PATH || "performance/results/kubernetes-load-summary.json";
  return {
    stdout: `\nServiceOps Kubernetes load summary\n${rendered}`,
    [outputPath]: rendered,
  };
}
