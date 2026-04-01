# HTTP API Reference

This document describes the HTTP API for MLSDM; readiness is tracked in [status/READINESS.md](status/READINESS.md).

## Quick Start

### Start the Server

```bash
# Development
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000

# Production with workers
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Basic Inference Request

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!", "moral_value": 0.7}'
```

Response:
```json
{
  "response": "Hello! I'm here to help...",
  "accepted": true,
  "phase": "wake",
  "moral_metadata": {
    "threshold": 0.5,
    "secure_mode": false,
    "applied_moral_value": 0.7
  },
  "timing": {"total": 45.2},
  "governance": null
}
```

---

## Endpoints

### Health Endpoints

#### `GET /health`

Simple health check. Returns `status: "healthy"` if the service is running.

**Response:**
```json
{"status": "healthy"}
```

**Use case:** Container liveness probe, basic health monitoring.

---

#### `GET /health/liveness`

Kubernetes-style liveness probe.

**Response:**
```json
{
  "status": "alive",
  "timestamp": 1732882427.123
}
```

**Use case:** Kubernetes liveness probe configuration.

---

#### `GET /health/readiness`

Kubernetes-style readiness probe. Returns 200 if ready, 503 if not.

**Response (200):**
```json
{
  "ready": true,
  "status": "ready",
  "timestamp": 1732882427.123,
  "checks": {
    "memory_manager": true,
    "memory_available": true,
    "cpu_available": true
  }
}
```

**Response (503):**
```json
{
  "ready": false,
  "status": "not_ready",
  "timestamp": 1732882427.123,
  "checks": {
    "memory_manager": false,
    "memory_available": true,
    "cpu_available": true
  }
}
```

**Use case:** Kubernetes readiness probe, load balancer health checks.

**Checks performed:**
- `memory_manager`: Engine is initialized
- `memory_available`: System memory < 95% usage
- `cpu_available`: CPU usage < 98%

---

#### `GET /health/metrics`

Prometheus metrics endpoint.

**Response:** Plain text in Prometheus format.

```
# HELP mlsdm_requests_total Total requests processed
# TYPE mlsdm_requests_total counter
mlsdm_requests_total 42
...
```

---

### Inference Endpoints

#### `POST /infer`

Main inference endpoint with full governance options.

**Request Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Input text (min 1 char) |
| `moral_value` | float | No | 0.5 | Moral threshold (0.0-1.0) |
| `max_tokens` | int | No | 512 | Max tokens to generate (1-4096) |
| `secure_mode` | bool | No | false | Enable enhanced security filtering |
| `aphasia_mode` | bool | No | false | Enable aphasia detection/repair |
| `rag_enabled` | bool | No | true | Enable RAG context retrieval |
| `context_top_k` | int | No | 5 | Number of context items for RAG |
| `user_intent` | string | No | null | Intent category hint |

**Response:**
| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Generated text |
| `accepted` | bool | Whether request was accepted |
| `phase` | string | Current phase (wake/sleep) |
| `moral_metadata` | object | Moral filter information |
| `rag_metadata` | object | RAG retrieval information |
| `aphasia_metadata` | object | Aphasia detection info (if enabled) |
| `timing` | object | Performance timing (ms) |
| `governance` | object | Full governance state |

**Example - Basic:**
```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?"}'
```

**Example - With Options:**
```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain neural networks",
    "moral_value": 0.6,
    "secure_mode": true,
    "aphasia_mode": true,
    "max_tokens": 256
  }'
```

**Secure Mode:**
When `secure_mode: true`, the moral threshold is boosted by 0.2:
- `moral_value: 0.5` → applied as `0.7`
- `moral_value: 0.9` → applied as `1.0` (capped)

---

#### `POST /generate`

Alternative generation endpoint with cognitive state information.

**Request Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Input text (min 1 char) |
| `moral_value` | float | No | 0.5 | Moral threshold (0.0-1.0) |
| `max_tokens` | int | No | 512 | Max tokens to generate |

**Response:**
| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Generated text |
| `accepted` | bool | Whether request was accepted |
| `phase` | string | Current phase |
| `moral_score` | float | Applied moral score |
| `aphasia_flags` | object | Aphasia detection flags |
| `emergency_shutdown` | bool | Shutdown status |
| `cognitive_state` | object | Cognitive state snapshot |

---

### Status Endpoint

#### `GET /status`

Extended service status with system information.

**Response:**
```json
{
  "status": "ok",
  "version": "1.2.0",
  "backend": "local_stub",
  "system": {
    "memory_mb": 45.32,
    "cpu_percent": 12.5
  },
  "config": {
    "dimension": 384,
    "rate_limiting_enabled": true
  }
}
```

---

## Error Responses

All errors return a structured JSON response:

```json
{
  "error": {
    "error_type": "validation_error",
    "message": "Prompt cannot be empty",
    "details": {"field": "prompt"}
  }
}
```

**Common Error Codes:**

| Status | error_type | Description |
|--------|------------|-------------|
| 400 | `validation_error` | Invalid input (e.g., whitespace prompt) |
| 422 | (Pydantic) | Schema validation failure |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |

---

## Rate Limiting

Default: 5 requests per second per client.

**Disable for testing:**
```bash
DISABLE_RATE_LIMIT=1 uvicorn mlsdm.api.app:app --port 8000
```

---

## Python SDK

```python
from sdk.python.client import MLSDMClient

client = MLSDMClient(base_url="http://localhost:8000")

# Health check
health = client.health()
print(health.status)  # "healthy"

# Inference
result = client.infer("What is AI?", moral_value=0.7)
print(result.response)
print(result.accepted)
print(result.phase)

# With secure mode
result = client.infer(
    "Explain quantum computing",
    moral_value=0.5,
    secure_mode=True
)
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_PATH` | `config/default_config.yaml` | Configuration file path |
| `LLM_BACKEND` | `local_stub` | LLM backend (local_stub, openai, anthropic) |
| `DISABLE_RATE_LIMIT` | `0` | Set to `1` to disable rate limiting |
| `OTEL_SDK_DISABLED` | `false` | Disable OpenTelemetry tracing |
| `OTEL_EXPORTER_TYPE` | `none` | Tracing exporter (console, otlp, jaeger) |

---

## Contract Stability

**STABLE Fields** (will not change without major version):
- `/infer`: `response`, `accepted`, `phase`
- `/health`: `status`
- `/health/readiness`: `ready`, `status`, `checks`

**UNSTABLE Fields** (may change in minor versions):
- `moral_metadata`, `rag_metadata`, `aphasia_metadata` structure
- `timing` keys
- `governance` structure

---

## See Also

- [ARCHITECTURE_SPEC.md](ARCHITECTURE_SPEC.md) - System architecture
- [OBSERVABILITY_GUIDE.md](OBSERVABILITY_GUIDE.md) - Metrics and logging
- [examples/http_inference_example.py](examples/http_inference_example.py) - Python examples
