# MLSDM Troubleshooting Guide (DOC-005)

A decision tree for diagnosing and resolving common MLSDM issues.

## Quick Diagnostic

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MLSDM Troubleshooting Decision Tree                  │
└─────────────────────────────────────────────────────────────────────────┘

Is the API responding?
├── NO → See: [API Not Responding](#1-api-not-responding)
└── YES → Are requests being rejected?
    ├── YES → Check the error code:
    │   ├── E1xx (Validation) → [Input Validation Errors](#2-input-validation-errors)
    │   ├── E2xx (Auth) → [Authentication Errors](#3-authentication-errors)
    │   ├── E3xx (Moral) → [Moral Filter Rejections](#4-moral-filter-rejections)
    │   ├── E5xx (Rhythm) → [Cognitive Rhythm Issues](#5-cognitive-rhythm-issues)
    │   ├── E6xx (LLM) → [LLM Provider Issues](#6-llm-provider-issues)
    │   ├── E7xx (System) → [System Errors](#7-system-errors)
    │   └── E9xx (API) → [Rate Limiting & API Errors](#8-rate-limiting-and-api-errors)
    └── NO → Are responses slow?
        ├── YES → [Performance Issues](#9-performance-issues)
        └── NO → Is quality degraded?
            └── YES → [Response Quality Issues](#10-response-quality-issues)
```

---

## 1. API Not Responding

### Symptoms
- Connection refused
- Connection timeout
- No response from server

### Decision Tree

```
API not responding?
├── Can you reach the host at all?
│   ├── NO → Check network connectivity, firewall, DNS
│   └── YES → Is the port open?
│       ├── NO → Check if service is running: `ps aux | grep uvicorn`
│       └── YES → Does /health/live respond?
│           ├── NO → Service is starting or crashed, check logs
│           └── YES → Does /health/ready respond?
│               ├── NO → Service is unhealthy, check dependencies
│               └── YES → Check for upstream issues (load balancer, etc.)
```

### Solutions

1. **Service not running:**
   ```bash
   # Check if service is running
   systemctl status mlsdm-api

   # Start service
   systemctl start mlsdm-api

   # Or start manually
   uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000
   ```

2. **Port blocked:**
   ```bash
   # Check if port is in use
   lsof -i :8000

   # Check firewall
   sudo ufw status
   ```

3. **Check logs:**
   ```bash
   # View service logs
   journalctl -u mlsdm-api -f

   # Or log files
   tail -f /var/log/mlsdm/mlsdm_observability.log
   ```

---

## 2. Input Validation Errors

### Error Codes
- `E100`: General validation error
- `E101`: Invalid vector dimension
- `E102`: Invalid moral value
- `E103`: Invalid prompt
- `E107`: Empty input
- `E108`: Input too long

### Decision Tree

```
Validation error?
├── E102 (moral_value) → Ensure 0.0 ≤ moral_value ≤ 1.0
├── E103/E107 (prompt) → Ensure prompt is non-empty string
├── E104 (max_tokens) → Ensure max_tokens is positive integer
└── E108 (too long) → Reduce prompt length (max: 10000 chars default)
```

### Solutions

```python
# Correct request format
{
    "prompt": "Your text here (non-empty, < 10000 chars)",
    "max_tokens": 256,       # Positive integer
    "moral_value": 0.8       # Between 0.0 and 1.0
}
```

---

## 3. Authentication Errors

### Error Codes
- `E201`: Invalid token
- `E202`: Expired token
- `E203`: Insufficient permissions
- `E204`: Invalid API key
- `E206`: Missing auth header

### Decision Tree

```
Auth error?
├── E206 (missing header) → Add Authorization header
├── E201/E204 (invalid) → Check API key or token is correct
├── E202 (expired) → Refresh or obtain new token
└── E203 (permissions) → Check user role has required permission
```

### Solutions

```bash
# API key auth
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Verify token is valid
curl -X GET http://localhost:8000/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 4. Moral Filter Rejections

### Error Codes
- `E301`: Moral threshold exceeded
- `E302`: Toxic content detected
- `E303`: Moral drift detected
- `E304`: Pre-flight rejection
- `E305`: Post-generation rejection

### Decision Tree

```
Moral rejection?
├── E301/E304 (pre-flight) → Input failed moral pre-check
│   └── Increase moral_value or modify prompt
├── E302 (toxic) → Content flagged as harmful
│   └── Review and modify input
└── E305 (post-gen) → Generated content failed check
    └── Retry with different prompt or lower creativity
```

### Solutions

1. **Check current threshold:**
   ```bash
   curl http://localhost:8000/state | jq '.moral_threshold'
   ```

2. **Adjust moral_value in request:**
   ```json
   {"prompt": "...", "moral_value": 0.9}
   ```

3. **Modify prompt to be more constructive**

---

## 5. Cognitive Rhythm Issues

### Error Codes
- `E501`: Sleep phase rejection
- `E502`: Phase transition failed
- `E503`: Consolidation timeout

### Decision Tree

```
Rhythm error?
├── E501 (sleep phase) → System is in sleep/consolidation phase
│   └── Wait or configure continuous operation
├── E502 (transition) → Phase transition issue
│   └── Check memory state, may need restart
└── E503 (timeout) → Consolidation taking too long
    └── Increase timeout or reduce memory size
```

### Solutions

```bash
# Check current phase
curl http://localhost:8000/state | jq '.phase'

# If stuck in sleep, check logs for consolidation issues
```

---

## 6. LLM Provider Issues

### Error Codes
- `E601`: LLM timeout
- `E602`: LLM rate limited
- `E603`: Empty response
- `E605`: Connection failed
- `E607`: Provider not found

### Decision Tree

```
LLM error?
├── E601 (timeout) → LLM taking too long
│   └── Increase timeout, reduce max_tokens, check provider status
├── E602 (rate limit) → Provider rate limit exceeded
│   └── Implement backoff, check quota
├── E603 (empty) → LLM returned nothing
│   └── Check prompt format, retry
├── E605 (connection) → Can't reach provider
│   └── Check network, API key, provider status
└── E607 (not found) → Invalid provider configured
    └── Check LLM_BACKEND env var
```

### Solutions

```bash
# Check LLM configuration
echo $OPENAI_API_KEY | head -c10

# Test provider directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check provider status
# https://status.openai.com/
```

---

## 7. System Errors

### Error Codes
- `E701`: Emergency shutdown
- `E702`: Resource exhausted
- `E703`: Circuit breaker open
- `E704`: Health check failed

### Decision Tree

```
System error?
├── E701 (emergency shutdown) → System entered emergency mode
│   └── Check logs for trigger, may need manual reset
├── E702 (resources) → Out of memory/CPU
│   └── Increase resources, reduce load
├── E703 (circuit breaker) → Too many failures
│   └── Wait for cooldown, check upstream
└── E704 (health failed) → Component unhealthy
    └── Check dependencies, restart
```

### Solutions

```bash
# Check emergency shutdown status
curl http://localhost:8000/state | jq '.emergency_shutdown'

# Check system resources
docker stats mlsdm-api
free -h
top -b -n1 | head -20

# Reset emergency shutdown (if applicable)
# Requires restart or manual intervention
```

---

## 8. Rate Limiting and API Errors

### Error Codes
- `E901`: Rate limit exceeded
- `E902`: Request timeout
- `E903`: Service unavailable

### Decision Tree

```
Rate/API error?
├── E901 (rate limit) → Too many requests
│   └── Implement backoff, check Retry-After header
├── E902 (timeout) → Request took too long
│   └── Reduce complexity, increase timeout
└── E903 (unavailable) → Service temporarily down
    └── Retry with exponential backoff
```

### Solutions

```python
import time
import httpx

def request_with_backoff(url, max_retries=3):
    for attempt in range(max_retries):
        response = httpx.post(url, json={"prompt": "Hello"})
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Max retries exceeded")
```

---

## 9. Performance Issues

### Symptoms
- High latency (P95 > 500ms)
- Slow response times
- Timeouts under load

### Decision Tree

```
Slow responses?
├── Is it consistently slow?
│   ├── YES → Check LLM provider, increase resources
│   └── NO → Check for load spikes, memory pressure
├── Which phase is slow?
│   ├── Pre-flight → Moral filter or embedding issue
│   ├── LLM call → Provider issue
│   └── Post-processing → Memory or consolidation issue
└── Is caching enabled?
    └── NO → Enable caching for repeated requests
```

### Solutions

1. **Check metrics:**
   ```bash
   curl http://localhost:8000/health/metrics | grep latency
   ```

2. **Enable caching:**
   ```bash
   export MLSDM_CACHE_ENABLED=true
   export MLSDM_CACHE_BACKEND=redis
   export MLSDM_REDIS_URL=redis://localhost:6379
   ```

3. **Reduce max_tokens** for faster responses

---

## 10. Response Quality Issues

### Symptoms
- Incoherent responses
- Aphasia detection (broken language)
- Low relevance

### Decision Tree

```
Quality issues?
├── Is aphasia being detected?
│   ├── YES → Check aphasia severity, repair may help
│   └── NO → May be prompt quality issue
├── Are responses off-topic?
│   └── Check prompt clarity, context retrieval
└── Are responses truncated?
    └── Increase max_tokens
```

### Solutions

1. **Check aphasia metrics:**
   ```bash
   curl http://localhost:8000/health/metrics | grep aphasia
   ```

2. **Improve prompt quality:**
   - Be specific and clear
   - Provide context
   - Use examples

3. **Adjust parameters:**
   ```json
   {
     "prompt": "Clear, specific prompt with context",
     "max_tokens": 512,
     "moral_value": 0.8
   }
   ```

---

## Common Issues Quick Reference

| Issue | Error Code | First Action |
|-------|------------|--------------|
| Connection refused | N/A | Check if service is running |
| Invalid token | E201 | Verify API key |
| Rate limited | E901 | Wait and retry with backoff |
| Moral rejection | E301 | Increase moral_value |
| LLM timeout | E601 | Check provider, reduce max_tokens |
| Emergency shutdown | E701 | Check logs, restart if needed |
| Slow responses | N/A | Enable caching, check metrics |

---

## Getting Help

1. **Check logs:** `/var/log/mlsdm/mlsdm_observability.log`
2. **Check metrics:** `http://localhost:8000/health/metrics`
3. **Review RUNBOOK.md:** For operational procedures
4. **Open issue:** https://github.com/neuron7xLab/mlsdm/issues
