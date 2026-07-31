# API examples

The commands below assume the default Compose ports. Spring API documentation is at
<http://localhost:8080/swagger-ui.html>; FastAPI documentation is at
<http://localhost:8000/docs>.

## Create a ticket

```bash
curl --fail-with-body \
  --request POST http://localhost:8080/api/tickets \
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
curl --fail-with-body http://localhost:8080/api/tickets
curl --fail-with-body http://localhost:8080/api/tickets/23dc7d80-d74f-4d56-8c8c-caf97dc9ed23
curl --fail-with-body \
  --request PATCH http://localhost:8080/api/tickets/23dc7d80-d74f-4d56-8c8c-caf97dc9ed23/status \
  --header "Content-Type: application/json" \
  --data '{"status":"IN_PROGRESS"}'
curl --fail-with-body http://localhost:8080/api/summary
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
  "modelVersion": "baseline-1"
}
```

The exact label and confidence depend on the bundled baseline dataset. `/model-info`
reports the model version, row count, and held-out validation scores.

## Health

```bash
curl --fail-with-body http://localhost:8080/actuator/health
curl --fail-with-body http://localhost:8000/health
curl --fail-with-body http://localhost:3000/health
```

Backend health includes database and Kafka connectivity. AI health returns `503` unless
the model is loaded and its Kafka worker has connected to broker metadata.
