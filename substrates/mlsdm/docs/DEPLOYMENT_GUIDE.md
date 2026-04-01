# Deployment Guide

**Document Version:** 1.2.0
**Project Version:** 1.2.0
**Last Updated:** December 2025
**Status:** Production

Production deployment guide for MLSDM Governed Cognitive Memory v1.2.0.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Requirements](#requirements)
- [Deployment Patterns](#deployment-patterns)
- [Configuration](#configuration)
- [Monitoring & Observability](#monitoring--observability)
- [Security Considerations](#security-considerations)
- [Scaling & Performance](#scaling--performance)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

---

## Deployment Overview

MLSDM can be deployed in several configurations:

1. **Standalone Python Application**: Direct integration into existing services
2. **FastAPI Microservice**: REST API with HTTP/JSON interface
3. **Docker Container**: Containerized deployment
4. **Kubernetes**: Scalable cloud deployment
5. **Serverless**: AWS Lambda, Google Cloud Functions (with considerations)

---

## Requirements

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 512 MB minimum, 1 GB recommended
- **Storage**: 100 MB for application, additional for logs
- **OS**: Linux, macOS, or Windows with Python 3.12+

### Python Requirements

```bash
Python >= 3.12
numpy >= 2.0.0
sentence-transformers >= 3.0.0  # Optional, for embeddings
fastapi >= 0.110.0  # If using API
uvicorn >= 0.29.0  # If using API
```

### Network Requirements

- **Outbound**: Access to LLM APIs (OpenAI, Anthropic, etc.)
- **Inbound**: Port 8000 (default FastAPI) or custom port

---

## Deployment Patterns

### Pattern 1: Standalone Integration

Simplest deployment - integrate directly into your Python application.

```python
# app.py
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

# Initialize once at startup
def create_wrapper():
    def my_llm(prompt: str, max_tokens: int) -> str:
        # Your LLM integration
        return call_your_llm(prompt, max_tokens)

    def my_embed(text: str) -> np.ndarray:
        # Your embedding integration
        return get_embeddings(text)

    return LLMWrapper(
        llm_generate_fn=my_llm,
        embedding_fn=my_embed,
        dim=384,
        capacity=20000
    )

# Global wrapper instance
wrapper = create_wrapper()

# Use in your application
def handle_request(user_input: str, moral_score: float) -> str:
    result = wrapper.generate(user_input, moral_score)
    if result["accepted"]:
        return result["response"]
    else:
        return f"Request rejected: {result['note']}"
```

**Pros:**
- Simple integration
- Low overhead
- Full control

**Cons:**
- Tied to application lifecycle
- Single process only
- No built-in API

---

### Pattern 2: FastAPI Microservice

Hardened REST API with async support (readiness tracked in [status/READINESS.md](status/READINESS.md)).

```python
# api_server.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np
from typing import Optional

app = FastAPI(title="MLSDM Cognitive API", version="1.0.0")

# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt")
    moral_value: float = Field(..., ge=0.0, le=1.0, description="Moral score")
    max_tokens: Optional[int] = Field(None, description="Max tokens override")
    context_top_k: int = Field(5, ge=1, le=20, description="Context items")

class GenerateResponse(BaseModel):
    response: str
    accepted: bool
    phase: str
    step: int
    note: str
    moral_threshold: float
    context_items: int

# Initialize wrapper
def get_wrapper():
    # Configure your LLM and embeddings
    def my_llm(prompt: str, max_tokens: int) -> str:
        # Implementation
        pass

    def my_embed(text: str) -> np.ndarray:
        # Implementation
        pass

    return LLMWrapper(
        llm_generate_fn=my_llm,
        embedding_fn=my_embed,
        dim=384
    )

wrapper = get_wrapper()

# Endpoints
@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text with cognitive governance."""
    try:
        result = wrapper.generate(
            prompt=request.prompt,
            moral_value=request.moral_value,
            max_tokens=request.max_tokens,
            context_top_k=request.context_top_k
        )
        return GenerateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/v1/state")
async def get_state():
    """Get system state."""
    return wrapper.get_state()

@app.get("/health")
async def health():
    """Health check endpoint."""
    state = wrapper.get_state()
    return {
        "status": "healthy",
        "step": state["step"],
        "phase": state["phase"],
        "memory_used": state["qilm_stats"]["used"],
        "memory_capacity": state["qilm_stats"]["capacity"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Run:**
```bash
# Development
uvicorn api_server:app --reload

# Production
uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
```

**Pros:**
- Standard REST API
- Built-in docs (Swagger UI)
- Easy to scale
- Language-agnostic clients

**Cons:**
- Additional complexity
- Network overhead

---

### Pattern 3: Docker Deployment

Containerized deployment for consistency and portability.

#### Dockerfile

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY api_server.py .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Local Docker Deployment

The repository includes a hardened docker-compose configuration (verify readiness in [status/READINESS.md](status/READINESS.md)):

```bash
# Quick start (uses Dockerfile.neuro-engine-service)
docker compose -f docker/docker-compose.yaml up -d

# Check health
curl http://localhost:8000/health

# Test generate endpoint
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "moral_value": 0.8}'

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

Or use Make targets:

```bash
# Build image
make docker-build-neuro-engine

# Run container
make docker-run-neuro-engine

# Run smoke tests
make docker-smoke-neuro-engine

# Docker compose up
make docker-compose-up

# Docker compose down
make docker-compose-down
```

#### docker-compose.yml

```yaml
services:
  neuro-engine:
    build:
      context: .
      dockerfile: Dockerfile.neuro-engine-service
    image: ghcr.io/neuron7xLab/mlsdm-neuro-engine:latest
    ports:
      - "8000:8000"
    environment:
      - LLM_BACKEND=${LLM_BACKEND:-local_stub}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - DISABLE_RATE_LIMIT=${DISABLE_RATE_LIMIT:-1}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

**Build and Run:**
```bash
# Build image
docker build -t mlsdm-cognitive:1.0.0 .

# Run container
docker run -d \
    --name mlsdm-api \
    -p 8000:8000 \
    -e OPENAI_API_KEY=$OPENAI_API_KEY \
    mlsdm-cognitive:1.0.0

# Or use docker-compose
docker-compose up -d
```

**Pros:**
- Consistent environment
- Easy deployment
- Isolated dependencies
- Portable across clouds

**Cons:**
- Container overhead
- Requires Docker knowledge

#### Container Image Verification (CICD-006, SEC-005)

All official container images are signed using [cosign](https://github.com/sigstore/cosign) with GitHub Actions OIDC keyless signing. SBOMs (Software Bill of Materials) are also attached.

**Verify container image signature:**

```bash
# Install cosign
brew install cosign  # macOS
# or: go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# Verify image signature (keyless OIDC verification)
cosign verify ghcr.io/neuron7xLab/mlsdm-neuro-engine:latest \
  --certificate-identity-regexp "https://github.com/neuron7xLab/mlsdm.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

**Retrieve SBOM from image:**

```bash
# Download SBOM attached to image
cosign download sbom ghcr.io/neuron7xLab/mlsdm-neuro-engine:latest > sbom.json

# View SBOM contents
cat sbom.json | jq '.components | length'  # Count dependencies
```

**SBOM Formats:**

- **CycloneDX**: `sbom-cyclonedx.json` - Attached to GitHub Release
- **SPDX**: `sbom-spdx.json` - Attached to GitHub Release

Both formats are industry-standard for supply chain security and vulnerability management.

---

### Pattern 4: Kubernetes Deployment

Scalable, production-grade deployment.

#### Deployment Manifest

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlsdm-api
  labels:
    app: mlsdm
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mlsdm
  template:
    metadata:
      labels:
        app: mlsdm
        version: v1.0.0
    spec:
      containers:
      - name: mlsdm-api
        image: your-registry/mlsdm-cognitive:1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: mlsdm-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: mlsdm-api-service
spec:
  selector:
    app: mlsdm
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mlsdm-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mlsdm-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Deploy:**
```bash
# Create secret
kubectl create secret generic mlsdm-secrets \
    --from-literal=openai-api-key=$OPENAI_API_KEY

# Deploy
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get pods -l app=mlsdm
kubectl get svc mlsdm-api-service
```

**Pros:**
- Auto-scaling
- Self-healing
- Load balancing
- Rolling updates

**Cons:**
- Kubernetes complexity
- Higher operational overhead

---

### Pattern 5: Canary Deployment (CICD-007)

Gradual rollout with traffic splitting for safe production updates.

#### Overview

Canary deployments allow testing new versions with a small percentage of traffic before full rollout. This minimizes risk by:

1. Running new version alongside stable version
2. Routing subset of traffic to canary
3. Monitoring error rates and latency
4. Promoting or rolling back based on metrics

#### Deployment Steps

```bash
# 1. Update canary image tag in manifest
# Edit deploy/k8s/canary-deployment.yaml, update image tag

# 2. Deploy canary (runs alongside stable)
kubectl apply -f deploy/k8s/canary-deployment.yaml

# 3. Verify canary is healthy
kubectl get pods -n mlsdm-canary -l track=canary
kubectl logs -n mlsdm-canary -l track=canary --tail=50

# 4. Monitor canary metrics (check for elevated error rates)
# Prometheus query: rate(http_requests_total{track="canary",status=~"5.."}[5m])

# 5a. If healthy: Promote canary to stable
kubectl set image deployment/mlsdm-api -n mlsdm-production \
  mlsdm-api=ghcr.io/neuron7xLab/mlsdm-neuro-engine:NEW_VERSION

# 5b. If unhealthy: Rollback canary
kubectl delete -f deploy/k8s/canary-deployment.yaml
```

#### Traffic Splitting (Service Mesh)

For percentage-based traffic splitting, use a service mesh (Istio, Linkerd):

**Istio VirtualService:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: mlsdm-vs
spec:
  hosts:
  - mlsdm-api
  http:
  - route:
    - destination:
        host: mlsdm-api
        subset: stable
      weight: 90
    - destination:
        host: mlsdm-api
        subset: canary
      weight: 10
```

**Header-based routing (for internal testing):**

```yaml
http:
- match:
  - headers:
      x-canary:
        exact: "true"
  route:
  - destination:
      host: mlsdm-api
      subset: canary
```

#### Rollback Procedure

```bash
# Immediate rollback (delete canary)
kubectl delete -f deploy/k8s/canary-deployment.yaml

# If promoted to stable, rollback to previous version
kubectl rollout undo deployment/mlsdm-api -n mlsdm-production

# Verify rollback
kubectl rollout status deployment/mlsdm-api -n mlsdm-production
```

#### Canary Success Criteria

Before promoting canary to stable, verify:

- [ ] Error rate < 0.1% (same as or better than stable)
- [ ] P95 latency < 500ms (per SLO_SPEC.md)
- [ ] No increase in emergency shutdown events
- [ ] Health checks passing for >15 minutes
- [ ] No abnormal log patterns

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# MLSDM Configuration
MLSDM_DIM=384
MLSDM_CAPACITY=20000
MLSDM_WAKE_DURATION=8
MLSDM_SLEEP_DURATION=3
MLSDM_INITIAL_THRESHOLD=0.50

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text

# API Configuration
API_PORT=8000
API_WORKERS=4
API_TIMEOUT=30

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090
```

### Configuration File

```yaml
# config.yaml
mlsdm:
  dimension: 384
  capacity: 20000
  wake_duration: 8
  sleep_duration: 3
  initial_threshold: 0.50

llm:
  provider: openai
  model: gpt-3.5-turbo
  max_tokens: 2048
  temperature: 0.7

embeddings:
  provider: sentence-transformers
  model: all-MiniLM-L6-v2
  dimension: 384

api:
  port: 8000
  workers: 4
  timeout: 30
  cors_origins:
    - "https://yourdomain.com"

logging:
  level: INFO
  format: json
  file: /var/log/mlsdm/app.log

monitoring:
  enabled: true
  metrics_port: 9090
  health_check_interval: 30
```

---

## Monitoring & Observability

### Key Metrics

**System Metrics:**
- `mlsdm_steps_total`: Total steps processed
- `mlsdm_accepted_total`: Accepted requests
- `mlsdm_rejected_total`: Rejected requests
- `mlsdm_memory_used`: Memory usage (vectors)
- `mlsdm_memory_bytes`: Memory usage (bytes)

**Performance Metrics:**
- `mlsdm_generation_duration_seconds`: Generation latency
- `mlsdm_retrieval_duration_seconds`: Context retrieval latency
- `mlsdm_moral_threshold`: Current moral threshold

**Phase Metrics:**
- `mlsdm_phase`: Current phase (0=wake, 1=sleep)
- `mlsdm_consolidations_total`: Total consolidations

### Prometheus Integration

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Metrics
requests_total = Counter('mlsdm_requests_total', 'Total requests')
accepted = Counter('mlsdm_accepted_total', 'Accepted requests')
rejected = Counter('mlsdm_rejected_total', 'Rejected requests')
memory_used = Gauge('mlsdm_memory_used', 'Memory vectors used')
moral_threshold = Gauge('mlsdm_moral_threshold', 'Moral threshold')
latency = Histogram('mlsdm_latency_seconds', 'Request latency')

# Start metrics server
start_http_server(9090)

# Update metrics
requests_total.inc()
memory_used.set(state['qilm_stats']['used'])
moral_threshold.set(state['moral_threshold'])
with latency.time():
    result = wrapper.generate(prompt, moral_value)
```

### Logging

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)

def log_request(request, result):
    """Log request with structured data."""
    log_data = {
        "timestamp": time.time(),
        "prompt_length": len(request["prompt"]),
        "moral_value": request["moral_value"],
        "accepted": result["accepted"],
        "phase": result["phase"],
        "step": result["step"],
        "moral_threshold": result["moral_threshold"]
    }
    logger.info(json.dumps(log_data))
```

### Health Checks

```python
@app.get("/health")
async def health():
    """Comprehensive health check."""
    state = wrapper.get_state()

    # Check memory usage
    memory_pct = (state['qilm_stats']['used'] /
                  state['qilm_stats']['capacity']) * 100

    # Check moral threshold bounds
    threshold_ok = 0.30 <= state['moral_threshold'] <= 0.90

    # Overall health
    healthy = memory_pct < 95 and threshold_ok

    return {
        "status": "healthy" if healthy else "degraded",
        "checks": {
            "memory": {
                "status": "ok" if memory_pct < 95 else "warning",
                "used": state['qilm_stats']['used'],
                "capacity": state['qilm_stats']['capacity'],
                "percentage": round(memory_pct, 2)
            },
            "moral_filter": {
                "status": "ok" if threshold_ok else "error",
                "threshold": state['moral_threshold']
            },
            "phase": {
                "current": state['phase'],
                "step": state['step']
            }
        }
    }
```

### Log Aggregation (OBS-005)

MLSDM supports centralized log aggregation with Grafana Loki. This enables:

- Centralized log search across all instances
- Correlation with Prometheus metrics
- Log-based alerting
- Trace correlation via trace_id

#### Quick Start with Loki

```bash
# Start the Loki stack (Loki + Promtail + Grafana)
cd deploy/monitoring/loki
docker compose up -d

# Access Grafana at http://localhost:3000 (admin/admin)
# Loki is pre-configured as a data source
```

#### Querying Logs (LogQL)

```logql
# All MLSDM logs
{job="mlsdm"}

# Filter by log level
{job="mlsdm"} | json | level="ERROR"

# View specific error codes
{job="mlsdm"} | json | error_code=~"E3.."

# Find logs for a specific request
{job="mlsdm"} | json | request_id="req-12345"

# High latency requests (>500ms)
{job="mlsdm"} | json | latency_ms > 500
```

See `deploy/monitoring/loki/logql-examples.md` for comprehensive query examples.

#### ELK Stack Alternative

For ELK (Elasticsearch, Logstash, Kibana) deployment, use a Filebeat configuration:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/mlsdm/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "mlsdm-logs-%{+yyyy.MM.dd}"

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
```

---

## Security Considerations

### API Security

1. **Authentication**
   ```python
   from fastapi import Header, HTTPException

   async def verify_api_key(x_api_key: str = Header()):
       if x_api_key != os.getenv("API_KEY"):
           raise HTTPException(status_code=401, detail="Invalid API key")

   @app.post("/v1/generate", dependencies=[Depends(verify_api_key)])
   async def generate(request: GenerateRequest):
       # ...
   ```

2. **Rate Limiting**
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter

   @app.post("/v1/generate")
   @limiter.limit("100/minute")
   async def generate(request: Request, ...):
       # ...
   ```

3. **Input Validation**
   ```python
   class GenerateRequest(BaseModel):
       prompt: str = Field(..., max_length=10000)
       moral_value: float = Field(..., ge=0.0, le=1.0)

       @validator('prompt')
       def validate_prompt(cls, v):
           if not v.strip():
               raise ValueError("Prompt cannot be empty")
           return v
   ```

### OAuth 2.0 / OIDC Authentication (SEC-004)

MLSDM supports OIDC authentication for enterprise deployments with identity providers like Auth0, Okta, Keycloak, Azure AD, and Google.

#### Configuration

Set environment variables to enable OIDC:

```bash
# Enable OIDC authentication
export MLSDM_OIDC_ENABLED=true

# OIDC issuer URL (your identity provider)
export MLSDM_OIDC_ISSUER=https://your-domain.auth0.com/

# Expected audience (API identifier or client ID)
export MLSDM_OIDC_AUDIENCE=https://api.mlsdm.example.com

# Optional: Custom roles claim (default: "roles")
export MLSDM_OIDC_ROLES_CLAIM=https://mlsdm.example.com/roles

# Optional: JWKS URI (auto-discovered if not set)
export MLSDM_OIDC_JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
```

#### Usage in FastAPI

```python
from fastapi import Depends
from mlsdm.security import (
    OIDCAuthenticator,
    OIDCAuthMiddleware,
    get_current_user,
    get_optional_user,
    require_oidc_auth,
    UserInfo,
)

# Initialize authenticator
authenticator = OIDCAuthenticator.from_env()

# Add middleware for automatic authentication
skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
# To protect /docs and /redoc, remove them explicitly (intentional override).
# Example: filtered_skip_paths = [path for path in skip_paths if path not in {"/docs", "/redoc"}]
app.add_middleware(
    OIDCAuthMiddleware,
    authenticator=authenticator,
    skip_paths=skip_paths,
)

# Use dependency injection for protected endpoints
@app.get("/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    return {"subject": user.subject, "roles": user.roles}

# Optional authentication
@app.get("/public")
async def public_endpoint(user: UserInfo | None = Depends(get_optional_user)):
    if user:
        return {"greeting": f"Hello, {user.name}"}
    return {"greeting": "Hello, anonymous"}

# Role-based access control with decorator
@require_oidc_auth(roles=["admin", "operator"])
@app.post("/admin/shutdown")
async def admin_shutdown(request: Request):
    return {"status": "shutdown initiated"}
```

#### Token Format

OIDC tokens should be passed as Bearer tokens:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer YOUR_OIDC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

#### Identity Provider Configuration

For Auth0:
1. Create an API in Auth0 Dashboard
2. Set identifier as `MLSDM_OIDC_AUDIENCE`
3. Use your Auth0 domain as `MLSDM_OIDC_ISSUER`
4. Add custom claims for roles if needed

For Azure AD:
1. Register an application in Azure AD
2. Configure API permissions
3. Set issuer to `https://login.microsoftonline.com/{tenant-id}/v2.0`
4. Set audience to your application client ID

For Keycloak:
1. Create a realm and client
2. Configure client for confidential access
3. Set issuer to `https://keycloak.example.com/realms/{realm}`
4. Enable role mapping in client scopes

### Network Security

- Use HTTPS/TLS for all external communication
- Implement CORS properly
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Network segmentation in Kubernetes

### Data Security

- Never log sensitive prompts or responses
- Sanitize outputs
- Implement audit logging
- Regular security updates

---

## Scaling & Performance

### Vertical Scaling

Single instance optimization:

```yaml
# Optimized configuration
mlsdm:
  capacity: 50000  # Increase for more memory

resources:
  requests:
    memory: "2Gi"
    cpu: "4000m"
```

### Horizontal Scaling

Multiple instances with load balancing:

- Each instance maintains its own memory (stateful)
- Use sticky sessions if context continuity needed
- Consider shared memory layer for advanced scenarios

### Performance Tuning

1. **Memory Capacity**
   - Default: 20,000 vectors (~30 MB)
   - High throughput: 50,000 vectors (~75 MB)
   - Low memory: 10,000 vectors (~15 MB)

2. **Phase Durations**
   - High throughput: wake=20, sleep=2
   - Balanced: wake=8, sleep=3 (default)
   - Frequent consolidation: wake=5, sleep=5

3. **Context Retrieval**
   - Fast: top_k=3
   - Balanced: top_k=5 (default)
   - Comprehensive: top_k=10

---

## Troubleshooting

### Common Issues

**Issue 1: High rejection rate**
```
Symptoms: Most requests rejected
Cause: Moral threshold too high or incorrect scoring
Solution:
- Check moral_value scoring function
- Lower initial_threshold
- Monitor threshold adaptation
```

**Issue 2: Memory full**
```
Symptoms: Context retrieval returns old data
Cause: Memory at capacity, wrapping occurs
Solution:
- Increase capacity parameter
- Implement memory cleanup strategy
- Monitor usage patterns
```

**Issue 3: Slow response times**
```
Symptoms: High P95/P99 latency
Cause: Large context_top_k or slow LLM
Solution:
- Reduce context_top_k
- Optimize embedding function
- Use faster LLM model
- Add caching layer
```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose logging
result = wrapper.generate(prompt, moral_value)

# Inspect state
state = wrapper.get_state()
print(json.dumps(state, indent=2))
```

---

## Production Checklist

Before deploying to production:

### Infrastructure
- [ ] Resources provisioned (CPU, RAM, storage)
- [ ] Network connectivity verified
- [ ] Load balancer configured
- [ ] SSL/TLS certificates installed
- [ ] DNS configured

### Application
- [ ] All tests passing
- [ ] Configuration validated
- [ ] Secrets management configured
- [ ] Error handling comprehensive
- [ ] Logging configured

### Monitoring
- [ ] Metrics collection enabled
- [ ] Dashboards created
- [ ] Alerts configured
- [ ] Health checks working
- [ ] Log aggregation setup

### Security
- [ ] Authentication enabled
- [ ] Rate limiting configured
- [ ] Input validation implemented
- [ ] Security scan passed
- [ ] Secrets rotated

### Operations
- [ ] Deployment procedure documented
- [ ] Rollback procedure tested
- [ ] Backup strategy defined
- [ ] Incident response plan ready
- [ ] On-call schedule established

### Performance
- [ ] Load testing completed
- [ ] Performance benchmarks met
- [ ] Resource limits tuned
- [ ] Scaling strategy defined
- [ ] Capacity planning done

### CI/CD & Branch Protection (CICD-002)
- [ ] Branch protection enabled on `main`
- [ ] Required status checks configured (lint, test, type-check)
- [ ] At least 1 approval required for PRs
- [ ] SLO-based release gates enabled (PERF-001)
- [ ] SBOM generation configured (SEC-005)
- [ ] Container image signing enabled (CICD-006)

---

## Branch Protection Configuration

The `main` branch should have branch protection rules configured to ensure code quality.

### Required Status Checks

Require the key CI jobs from these workflows: `ci-neuro-cognitive-engine`, `ci-smoke`, `property-tests`, `dependency-review`, `sast-scan`.

| Check Name | Workflow | Description |
|------------|----------|-------------|
| `Lint and Type Check` | `ci-neuro-cognitive-engine.yml` | Ruff linting and mypy type checking |
| `Security Vulnerability Scan` | `ci-neuro-cognitive-engine.yml` | pip-audit dependency scanning |
| `test (3.11)` | `ci-neuro-cognitive-engine.yml` | Unit tests on Python 3.11 (default PR matrix) |
| `Code Coverage Gate` | `ci-neuro-cognitive-engine.yml` | Coverage threshold + core module coverage |
| `End-to-End Tests` | `ci-neuro-cognitive-engine.yml` | E2E integration tests |
| `Effectiveness Validation` | `ci-neuro-cognitive-engine.yml` | SLO and effectiveness validation |
| `Smoke Tests` | `ci-smoke.yml` | Fast unit smoke suite |
| `Coverage Gate` | `ci-smoke.yml` | Coverage gate quick check |
| `Ablation Smoke Test` | `ci-smoke.yml` | Ablation baseline smoke checks |
| `Policy Check` | `ci-smoke.yml` | CI policy conftest validation |
| `Property-Based Invariants Tests (3.11)` | `property-tests.yml` | Property-based invariants (default matrix) |
| `Counterexamples Regression Tests` | `property-tests.yml` | Counterexample regression suite |
| `Invariant Coverage Check` | `property-tests.yml` | Invariant documentation coverage |
| `Dependency Review` | `dependency-review.yml` | Dependency diff/vulnerability review |
| `Bandit SAST Scan` | `sast-scan.yml` | Bandit static analysis |
| `Semgrep SAST Scan` | `sast-scan.yml` | Semgrep security analysis |
| `Dependency Vulnerability Scan` | `sast-scan.yml` | pip-audit vulnerability gate |
| `Secrets Scanning` | `sast-scan.yml` | Gitleaks secrets scan |

### Configuration via GitHub CLI

```bash
# Enable branch protection with required status checks
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Lint and Type Check","Security Vulnerability Scan","test (3.11)","Code Coverage Gate","End-to-End Tests","Effectiveness Validation","Smoke Tests","Coverage Gate","Ablation Smoke Test","Policy Check","Property-Based Invariants Tests (3.11)","Counterexamples Regression Tests","Invariant Coverage Check","Dependency Review","Bandit SAST Scan","Semgrep SAST Scan","Dependency Vulnerability Scan","Secrets Scanning"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null

# Verify branch protection
gh api repos/{owner}/{repo}/branches/main/protection
```

### Recommended Settings

- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require at least 1 approval
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require approval for workflow runs from forked repositories
- ❌ Do not allow bypassing the above settings

### Trusted PR Auto-Approval (Forks)

To avoid `action_required` runs for trusted contributors, enable the auto-approval workflow:

1. Ensure `.github/workflows/trusted-pr-auto-approve.yml` is present.
2. Set the repository variable `TRUSTED_PR_ACTORS` to a comma-separated list of GitHub logins that are allowed to auto-approve forked PR workflows.
3. Trusted authors with association `OWNER`, `MEMBER`, or `COLLABORATOR` are auto-approved without manual intervention; all other forked PRs still require manual approval.

**Verification**

- Open a PR from a fork by an untrusted contributor → workflows remain `action_required` until a maintainer approves.
- Open a PR from a trusted contributor (or one listed in `TRUSTED_PR_ACTORS`) → workflows auto-approve and start running shortly after the PR event.

---

## Support

For deployment assistance:
- GitHub Issues: https://github.com/neuron7xLab/mlsdm/issues
- Documentation: See README.md and other guides
- Email: Contact maintainer for enterprise support

---

**Version**: 1.0.0
**Last Updated**: November 2025
**Maintainer**: neuron7x
