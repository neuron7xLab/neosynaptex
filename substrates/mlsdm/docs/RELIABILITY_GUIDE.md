# MLSDM Reliability Guide

**Status**: See [status/READINESS.md](status/READINESS.md) (not yet verified)
**Last Updated**: November 2025
**Maintainer**: neuron7x

## Table of Contents

1. [Overview](#overview)
2. [Reliability Patterns](#reliability-patterns)
3. [Bulkhead Pattern](#bulkhead-pattern)
4. [Circuit Breaker](#circuit-breaker)
5. [Auto-Recovery](#auto-recovery)
6. [Graceful Degradation](#graceful-degradation)
7. [Configuration](#configuration)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Overview

MLSDM implements a comprehensive reliability layer to ensure production stability:

- **Bulkhead Pattern**: Isolates subsystems to prevent cascading failures
- **Circuit Breaker**: Protects against repeated failures in external services
- **Auto-Recovery**: Automatically recovers from emergency shutdown states
- **Graceful Degradation**: Falls back to stateless mode when memory fails

These patterns work together to maintain system availability and predictable behavior under adverse conditions.

---

## Reliability Patterns

### Defense in Depth

MLSDM uses multiple layers of protection:

```
Request
   │
   ▼
┌─────────────────────┐
│  Rate Limiter       │  ← Prevents abuse
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Bulkhead           │  ← Limits concurrency per subsystem
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Circuit Breaker    │  ← Protects external calls (embedding/LLM)
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Retry with Backoff │  ← Handles transient failures
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Graceful Fallback  │  ← Stateless mode if memory fails
└─────────────────────┘
```

---

## Bulkhead Pattern

The bulkhead pattern compartmentalizes system resources to prevent cascading failures. Each subsystem has its own concurrency limit.

### Compartments

| Compartment     | Default Limit | Purpose                          |
|-----------------|---------------|----------------------------------|
| LLM_GENERATION  | 10           | LLM API calls (external, slow)   |
| EMBEDDING       | 20           | Embedding operations             |
| MEMORY          | 50           | PELM/Synaptic memory operations  |
| COGNITIVE       | 100          | General cognitive processing     |

### How It Works

1. Before an LLM operation, the engine acquires a slot in the `LLM_GENERATION` compartment
2. If all slots are in use, the request waits up to `bulkhead_timeout` seconds
3. If timeout expires, a `bulkhead_full` error is returned
4. After the operation completes (success or failure), the slot is released

### Configuration

```python
from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig

config = NeuroEngineConfig(
    # Enable/disable bulkhead (default: True)
    enable_bulkhead=True,

    # Maximum wait time to acquire a slot (seconds)
    bulkhead_timeout=5.0,

    # Concurrency limits per compartment
    bulkhead_llm_limit=10,
    bulkhead_embedding_limit=20,
    bulkhead_memory_limit=50,
    bulkhead_cognitive_limit=100,
)

engine = NeuroCognitiveEngine(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    config=config,
)
```

### Observability

Get bulkhead state:

```python
state = engine.get_bulkhead_state()
# Returns:
# {
#     "enabled": True,
#     "compartments": {
#         "llm_generation": {
#             "current_active": 3,
#             "max_concurrent": 10,
#             "total_acquired": 1000,
#             "total_rejected": 5,
#             "avg_wait_ms": 12.5
#         },
#         ...
#     },
#     "summary": {
#         "total_active": 15,
#         "total_acquired": 2500,
#         "total_rejected": 10,
#         "rejection_rate": 0.004
#     }
# }
```

### Error Handling

When bulkhead is full:

```python
result = engine.generate(prompt="Hello")
if result.get("error") and result["error"]["type"] == "bulkhead_full":
    # System is at capacity
    # Options:
    # 1. Retry later
    # 2. Return 503 Service Unavailable
    # 3. Queue the request
    print(f"System at capacity: {result['error']['message']}")
```

---

## Circuit Breaker

Protects against cascading failures from external services (embedding API).

### States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are blocked for recovery
- **HALF_OPEN**: Testing if service recovered

### Configuration

```python
# Defaults from calibration
failure_threshold: 5      # Failures before opening
recovery_timeout: 60.0    # Seconds before testing recovery
success_threshold: 2      # Successes to close circuit
```

### Behavior

```python
state = wrapper.get_state()
cb_state = state["reliability"]["circuit_breaker_state"]
# "closed" | "open" | "half_open"
```

---

## Auto-Recovery

The CognitiveController automatically recovers from emergency shutdown states.

### Recovery Conditions

1. **Cooldown period**: Sufficient steps have passed since shutdown
2. **Memory safety**: Memory usage is below safety threshold
3. **Attempt limit**: Recovery attempts haven't exceeded maximum

### Configuration

From `config/calibration.py`:

```python
recovery_cooldown_steps: 10       # Steps before attempting recovery
recovery_memory_safety_ratio: 0.8 # Memory must be below threshold * ratio
recovery_max_attempts: 3          # Max recovery attempts per shutdown
```

### Manual Reset

```python
controller = CognitiveController(dim=384)

# If stuck in emergency state
if controller.is_emergency_shutdown():
    # Option 1: Wait for auto-recovery
    # Option 2: Manual reset (use with caution)
    controller.reset_emergency_shutdown()
```

---

## Graceful Degradation

When PELM (memory) fails repeatedly, the system degrades to stateless mode.

### Trigger

After `pelm_failure_threshold` (default: 3) consecutive failures:

```python
wrapper.stateless_mode = True
```

### Behavior in Stateless Mode

- Memory operations are skipped
- Context retrieval returns empty results
- LLM generation still works
- Response includes `"stateless_mode": True`

### Recovery

```python
wrapper.reset()  # Resets all failure counters and stateless mode
```

---

## Configuration

### Full Configuration Example

```python
from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig

config = NeuroEngineConfig(
    # Core settings
    dim=384,
    capacity=20_000,

    # Reliability: Bulkhead
    enable_bulkhead=True,
    bulkhead_timeout=5.0,
    bulkhead_llm_limit=10,
    bulkhead_embedding_limit=20,
    bulkhead_memory_limit=50,
    bulkhead_cognitive_limit=100,

    # Reliability: LLM
    llm_timeout=30.0,
    llm_retry_attempts=3,

    # Observability
    enable_metrics=True,
)
```

### YAML Configuration

Add to `config/production.yaml`:

```yaml
# Reliability settings
reliability:
  bulkhead:
    enabled: true
    timeout_seconds: 5.0
    llm_limit: 10
    embedding_limit: 20
    memory_limit: 50
    cognitive_limit: 100

  llm:
    timeout: 30.0
    retry_attempts: 3
```

---

## Monitoring

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `bulkhead_rejection_rate` | Rate of bulkhead rejections | > 0.05 |
| `circuit_breaker_state` | "open" indicates service failure | = "open" |
| `stateless_mode` | True indicates degraded operation | = True |
| `emergency_shutdown` | True indicates critical failure | = True |

### Prometheus Metrics

```
# Bulkhead metrics
mlsdm_bulkhead_active{compartment="llm_generation"} 3
mlsdm_bulkhead_acquired_total{compartment="llm_generation"} 1000
mlsdm_bulkhead_rejected_total{compartment="llm_generation"} 5

# Circuit breaker
mlsdm_circuit_breaker_state{service="embedding"} 0  # 0=closed, 1=open, 2=half_open

# Reliability state
mlsdm_stateless_mode 0
mlsdm_emergency_shutdown 0
```

---

## Troubleshooting

### Bulkhead Full Errors

**Symptom**: Requests fail with `bulkhead_full` error

**Causes**:
1. LLM service is slow
2. High concurrent load
3. Bulkhead limits too low

**Solutions**:
1. Increase `bulkhead_llm_limit`
2. Increase `bulkhead_timeout`
3. Scale horizontally
4. Implement request queuing

### Circuit Breaker Open

**Symptom**: All embedding requests fail with "circuit breaker is OPEN"

**Causes**:
1. Embedding service is down
2. Network issues

**Solutions**:
1. Wait for `recovery_timeout` (60s default)
2. Check embedding service health
3. Manual reset: `wrapper.embedding_circuit_breaker.reset()`

### Stateless Mode Active

**Symptom**: Responses include `"stateless_mode": True`

**Causes**:
1. PELM memory corruption
2. Repeated memory errors

**Solutions**:
1. Call `wrapper.reset()` to clear state
2. Check memory pressure
3. Review logs for PELM errors

### Emergency Shutdown

**Symptom**: All requests rejected with "emergency shutdown"

**Causes**:
1. Memory limit exceeded
2. Processing timeout

**Solutions**:
1. Wait for auto-recovery (10 steps)
2. Manual reset: `controller.reset_emergency_shutdown()`
3. Reduce memory pressure

---

## References

- [Bulkhead Pattern (Microsoft)](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Release It! by Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)
