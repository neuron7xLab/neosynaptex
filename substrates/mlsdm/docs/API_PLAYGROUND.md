# MLSDM API Playground (DOC-004)

Interactive examples for the MLSDM API. These examples can be run directly
or imported into tools like Postman, Insomnia, or curl.

## Quick Start

```bash
# Start the API server
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000
```

## Interactive Endpoints

### 1. Health Check

```bash
# Simple health check
curl http://localhost:8000/health

# Detailed health with metrics
curl http://localhost:8000/health/ready

# Liveness probe (for Kubernetes)
curl http://localhost:8000/health/live
```

### 2. Text Generation

**Basic Generation:**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "max_tokens": 256
  }'
```

**With Moral Value:**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a helpful guide for beginners",
    "max_tokens": 512,
    "moral_value": 0.9
  }'
```

**With Request ID (for tracing):**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-custom-request-id-123" \
  -d '{
    "prompt": "Summarize this text briefly",
    "max_tokens": 100
  }'
```

### 3. System State

```bash
# Get current cognitive state
curl http://localhost:8000/state

# Example response:
# {
#   "phase": "wake",
#   "step": 42,
#   "moral_threshold": 0.52,
#   "memory_usage": 1234,
#   "emergency_shutdown": false
# }
```

### 4. Metrics (Prometheus)

```bash
# Get Prometheus-formatted metrics
curl http://localhost:8000/health/metrics
```

## Python Client Examples

### Basic Usage

```python
import httpx

# Initialize client
client = httpx.Client(base_url="http://localhost:8000")

# Generate text
response = client.post("/generate", json={
    "prompt": "Write a haiku about AI",
    "max_tokens": 50
})
result = response.json()
print(result["text"])
```

### Async Client

```python
import asyncio
import httpx

async def generate_async():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/generate", json={
            "prompt": "Explain machine learning",
            "max_tokens": 200
        })
        return response.json()

result = asyncio.run(generate_async())
print(result["text"])
```

### With Authentication

```python
import httpx

client = httpx.Client(
    base_url="http://localhost:8000",
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)

response = client.post("/generate", json={
    "prompt": "Secure generation request",
    "max_tokens": 100
})
```

### Error Handling

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

try:
    response = client.post("/generate", json={
        "prompt": "Test prompt",
        "max_tokens": 100
    })
    response.raise_for_status()
    result = response.json()
    print(f"Generated: {result['text']}")
except httpx.HTTPStatusError as e:
    error = e.response.json()
    print(f"Error {error['error']['error_code']}: {error['error']['message']}")
except httpx.RequestError as e:
    print(f"Request failed: {e}")
```

## JavaScript/TypeScript Examples

### Fetch API

```javascript
const response = await fetch('http://localhost:8000/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Write a poem about nature',
    max_tokens: 100
  })
});

const result = await response.json();
console.log(result.text);
```

### With Axios

```javascript
const axios = require('axios');

const response = await axios.post('http://localhost:8000/generate', {
  prompt: 'Explain recursion',
  max_tokens: 200
});

console.log(response.data.text);
```

## Postman Collection

Import this collection into Postman:

```json
{
  "info": {
    "name": "MLSDM API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health"
      }
    },
    {
      "name": "Generate Text",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/generate",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"prompt\": \"Your prompt here\", \"max_tokens\": 256}"
        }
      }
    },
    {
      "name": "Get State",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/state"
      }
    },
    {
      "name": "Prometheus Metrics",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health/metrics"
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    }
  ]
}
```

## Response Examples

### Successful Generation

```json
{
  "text": "Generated text content here...",
  "timing": {
    "total_ms": 45.2,
    "moral_precheck": 2.1,
    "llm_call": 40.3,
    "post_processing": 2.8
  },
  "accepted": true,
  "moral_score": 0.85,
  "phase": "wake",
  "step": 123
}
```

### Moral Rejection

```json
{
  "error": {
    "error_code": "E301",
    "message": "Moral threshold exceeded",
    "details": {
      "score": 0.35,
      "threshold": 0.50
    },
    "recoverable": true
  }
}
```

### Rate Limit Error

```json
{
  "error": {
    "error_code": "E901",
    "message": "Rate limit exceeded",
    "recoverable": true,
    "retry_after": 60
  }
}
```

## OpenAPI/Swagger UI

Interactive documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) - Full API documentation
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Troubleshooting guide
- [OBSERVABILITY_GUIDE.md](OBSERVABILITY_GUIDE.md) - Monitoring setup
