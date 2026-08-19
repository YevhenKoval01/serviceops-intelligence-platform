# API examples

The commands below assume the default Compose ports. Spring API documentation is at
<http://localhost:8080/swagger-ui.html>; FastAPI documentation is at
<http://localhost:8000/docs>.

## Sign in

Exchange a local account for a 15-minute bearer token:

```bash
curl --fail-with-body \
  --request POST http://localhost:8080/api/auth/login \
  --header "Content-Type: application/json" \
  --data '{"username":"operator","password":"operator_dev_2026"}'
```

The response includes `accessToken`, `tokenType`, `expiresIn`, `expiresAt`, and the
authenticated user. Assign the returned token before running the protected examples:

```bash
TOKEN="paste-accessToken-here"
```

The known credentials are for isolated local development only. `viewer` /
`viewer_dev_2026` can call read endpoints but receives `403` for ticket mutations and
direct prediction.

## Create a ticket

```bash
curl --fail-with-body \
  --request POST http://localhost:8080/api/tickets \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "title": "Production API unavailable",
    "description": "Every customer API request returns a server error and order processing is blocked.",
    "reportedPriority": "HIGH"
  }'
```

The API returns `201 Created`. Prediction fields are initially nullable because inference
is asynchronous:

```json
{
  "id": "23dc7d80-d74f-4d56-8c8c-caf97dc9ed23",
  "title": "Production API unavailable",
  "description": "Every customer API request returns a server error and order processing is blocked.",
  "status": "OPEN",
  "reportedPriority": "HIGH",
  "predictedPriority": null,
  "predictedCategory": null,
  "predictionConfidence": null,
  "modelVersion": null,
  "createdAt": "2026-07-30T10:00:00Z",
  "updatedAt": "2026-07-30T10:00:00Z",
  "version": 0
}
```

## Read and update tickets

```bash
curl --fail-with-body --header "Authorization: Bearer $TOKEN" http://localhost:8080/api/tickets
curl --fail-with-body --header "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/tickets/23dc7d80-d74f-4d56-8c8c-caf97dc9ed23
curl --fail-with-body \
  --request PATCH http://localhost:8080/api/tickets/23dc7d80-d74f-4d56-8c8c-caf97dc9ed23/status \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"status":"IN_PROGRESS"}'
curl --fail-with-body --header "Authorization: Bearer $TOKEN" http://localhost:8080/api/summary
```

Summary responses contain `total`, `open`, `inProgress`, and `resolved` counts.

## Validation problem

Invalid Spring requests use RFC 7807-compatible `application/problem+json`:

```json
{
  "type": "https://serviceops.local/problems/validation",
  "title": "Validation failed",
  "status": 400,
  "detail": "One or more request fields are invalid",
  "instance": "/api/tickets",
  "errors": {
    "title": "size must be between 5 and 150",
    "description": "size must be between 10 and 4000"
  }
}
```

## Direct model prediction

The normal application path uses Kafka. This endpoint is useful for inspecting the
model independently:

```bash
curl --fail-with-body \
  --request POST http://localhost:8000/predict \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "title": "Production API unavailable",
    "description": "Every customer API request returns a server error and order processing is blocked."
  }'
```

```json
{
  "category": "TECHNICAL",
  "priority": "HIGH",
  "confidence": 0.87542,
  "modelVersion": "baseline-2"
}
```

The exact label and confidence depend on the bundled baseline dataset. `/model-info`
reports the model version, row count, and held-out validation scores.

## Ask the knowledge assistant

Both roles can ask a question. The UI calls the same-origin `/assistant/ask` proxy; direct
AI-service clients can use `/knowledge/ask` with the same body and token.

```bash
curl --fail-with-body \
  --request POST http://localhost:3000/assistant/ask \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"question":"How should I investigate repeated HTTP 500 API errors?"}'
```

```json
{
  "answer": "The ServiceOps knowledge base recommends:\n- Record the affected endpoint and one correlation identifier. [1]",
  "grounded": true,
  "citations": [
    {
      "documentId": "technical-api-errors",
      "title": "API error triage",
      "section": "Establish impact",
      "revision": "2026-08-05",
      "sourcePath": "knowledge/technical-api-errors.md",
      "excerpt": "Record the affected endpoint, region, first observed time in UTC, HTTP status, request correlation identifier, and whether retries succeed.",
      "relevance": 0.42
    }
  ],
  "indexVersion": "tfidf-extractive-1-<content-digest>"
}
```

When no source supports the question, `grounded` is `false`, `citations` is empty, and the
answer directs the user to human review. Clients must not treat an abstention as operational
guidance.

## Health

```bash
curl --fail-with-body http://localhost:8080/actuator/health
curl --fail-with-body http://localhost:8000/health
curl --fail-with-body http://localhost:3000/health
```

Backend health includes database and Kafka connectivity. AI health returns `503` unless
the model is loaded and its Kafka worker has connected to broker metadata.

Health and OpenAPI documents are intentionally public. `/api/**`, `/predict`,
`/model-info`, `/knowledge/ask`, and `/assistant/ask` enforce authentication as described
above.
