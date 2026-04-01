# ADR-0004: Memory Bounds Invariant (CORE-04)

**Status**: Accepted
**Date**: 2025-11-30
**Deciders**: MLSDM Core Team
**Categories**: Architecture, Performance, Reliability

## Context

MLSDM is designed for deployment in resource-constrained environments, including:
- Edge devices with limited RAM
- Container environments with memory limits
- Multi-tenant systems with resource quotas
- Long-running services that must not leak memory

The system combines multiple memory subsystems:
- **PELM** (Phase-Entangled Lattice Memory): Semantic vector storage
- **MultiLevelSynapticMemory**: L1/L2/L3 hierarchical memory
- **Controller buffers**: Caches, locks, internal state

Without explicit bounds, these components could grow unboundedly, leading to:
- Out-of-memory (OOM) kills in containerized deployments
- Resource starvation in shared environments
- Unpredictable behavior under load
- Memory fragmentation over time

### Key Forces

- **Predictability**: Operators need to know maximum resource consumption
- **Reliability**: OOM kills are catastrophic failures
- **Edge deployment**: Must work on devices with <2GB RAM
- **Long-running**: No memory growth over weeks/months of operation
- **Performance**: Memory checks must not add significant overhead

### The CORE-04 Invariant

The project defines a critical invariant:

> **CORE-04**: Total memory usage MUST NOT exceed 1.4 GB under any circumstances

This bound was chosen to allow:
- Safe operation on 2GB containers with headroom
- Predictable resource allocation
- Co-location with other services

## Decision

We will implement and enforce a **global memory bound** (CORE-04) through:

1. **Component-level memory tracking**: Each memory component reports its usage
2. **Aggregated memory calculation**: Controller sums all component memory
3. **Hard limit enforcement**: Emergency shutdown if bound exceeded
4. **Automatic recovery**: System can recover after memory pressure subsides

### Memory Tracking API

Each memory component implements:

```python
def memory_usage_bytes(self) -> int:
    """Return current memory usage in bytes."""
```

The CognitiveController aggregates:

```python
def memory_usage_bytes(self) -> int:
    pelm_bytes = self.pelm.memory_usage_bytes()
    synaptic_bytes = self.synaptic.memory_usage_bytes()
    controller_overhead = 4096  # ~4KB internal structures
    return pelm_bytes + synaptic_bytes + controller_overhead
```

### Enforcement Points

1. **Process event**: Check before and after memory-modifying operations
2. **Health endpoint**: Report current memory usage and bound
3. **Metrics**: Export `mlsdm_memory_usage_bytes` gauge

### Emergency Shutdown

When memory bound is exceeded:

```python
if current_memory_bytes > max_memory_bytes:
    self._enter_emergency_shutdown("memory_limit_exceeded")
```

Emergency shutdown:
- Blocks all new event processing
- Logs warning with memory stats
- Sets `emergency_shutdown = True`
- Can auto-recover after cooldown if memory drops below safety threshold

### Memory Budget Allocation

| Component | Formula | Default |
|-----------|---------|---------|
| PELM | `capacity × (dim + 2) × 4` | ~30.88 MB |
| Synaptic L1 | `capacity × dim × 4` | ~1.47 MB |
| Synaptic L2 | `capacity × dim × 4` | ~1.47 MB |
| Synaptic L3 | `capacity × dim × 4` | ~1.47 MB |
| Controller | Fixed | ~4 KB |
| **Total** | Sum | ~35.3 MB |

With default settings, memory usage is well under the 1.4 GB bound.

### Configuration

```python
# Default max memory bytes: 1.4 GiB (~1.5 GB)
# Uses binary units (1024^3) for consistency with container memory limits
_DEFAULT_MAX_MEMORY_BYTES = int(1.4 * 1024**3)  # 1,503,238,553 bytes

class CognitiveController:
    def __init__(
        self,
        max_memory_bytes: int | None = None,  # Override bound
        ...
    ):
        self.max_memory_bytes = max_memory_bytes or _DEFAULT_MAX_MEMORY_BYTES
```

## Consequences

### Positive

- **Predictable resource usage**: Operators can size containers accurately
- **No OOM kills**: System shuts down gracefully before OOM
- **Edge-ready**: Works on resource-constrained devices
- **Observable**: Memory metrics enable capacity planning
- **Recoverable**: Auto-recovery reduces operational burden
- **Testable**: Invariant verified in property-based tests

### Negative

- **Reduced capacity**: Cannot store infinite vectors
- **Check overhead**: Memory calculation adds ~1μs per event
- **Emergency state**: Requires recovery procedure (automatic or manual)
- **Conservative bound**: 1.4 GB may be too restrictive for some deployments

### Neutral

- Memory bound is configurable per deployment
- Default bound optimizes for 2GB container headroom
- Components must implement `memory_usage_bytes()` interface

## Alternatives Considered

### Alternative 1: No Memory Bound

- **Description**: Trust component-level capacity limits only
- **Pros**: Simpler, no aggregation logic
- **Cons**: No global guarantee, Python object overhead can grow
- **Reason for rejection**: Insufficient for production deployments with hard limits

### Alternative 2: Memory Profiler Integration

- **Description**: Use `tracemalloc` or similar for exact tracking
- **Pros**: Accurate byte-level tracking
- **Cons**: Significant performance overhead (10-30% slowdown)
- **Reason for rejection**: Overhead not acceptable for production

### Alternative 3: OS-level Limits Only

- **Description**: Rely on container memory limits, cgroups, ulimits
- **Pros**: Standard tooling, no application code needed
- **Cons**: OOM kills are disruptive, no graceful degradation
- **Reason for rejection**: Application needs to participate in resource management

### Alternative 4: Eviction-based Memory Management

- **Description**: Evict oldest entries when approaching limit
- **Pros**: Continuous operation without shutdown
- **Cons**: Complex eviction policy, may lose important context
- **Reason for rejection**: Emergency shutdown is simpler and safer; eviction can be added later

### Alternative 5: Dynamic Memory Allocation

- **Description**: Grow/shrink capacity based on available system memory
- **Pros**: Adapts to environment, maximizes utilization
- **Cons**: Complex, non-deterministic behavior, potential fragmentation
- **Reason for rejection**: Predictable fixed bounds preferred for production

## Implementation

### Affected Components

- `src/mlsdm/core/cognitive_controller.py` - Enforcement and tracking
- `src/mlsdm/memory/phase_entangled_lattice_memory.py` - PELM memory tracking
- `src/mlsdm/memory/multi_level_memory.py` - Synaptic memory tracking
- `src/mlsdm/api/health.py` - Memory health checks
- `src/mlsdm/observability/metrics.py` - Memory metrics
- `tests/property/test_invariants_memory.py` - Property tests
- `config/calibration.py` - Default bounds

### Key Invariants

From `docs/FORMAL_INVARIANTS.md`:

- **INV-LLM-S1**: `memory_usage() ≤ 1.4 × 10^9 bytes`
- **INV-LLM-S2**: `|memory_vectors| ≤ capacity`

### Recovery Configuration

```python
# Recovery parameters (from calibration)
_CC_RECOVERY_COOLDOWN_STEPS = 10     # Steps before recovery attempt
_CC_RECOVERY_MEMORY_SAFETY_RATIO = 0.8  # Must be below 80% of threshold
_CC_RECOVERY_MAX_ATTEMPTS = 3        # Maximum recovery attempts
```

### Metrics

- `mlsdm_memory_usage_bytes` - Current total memory (gauge)
- `mlsdm_memory_limit_bytes` - Configured limit (gauge)
- `mlsdm_emergency_shutdown_active` - Shutdown state (gauge)
- `mlsdm_emergency_shutdown_total` - Shutdown count (counter)

### Health Check Response

```json
{
  "memory": {
    "current_bytes": 35123456,
    "max_bytes": 1503238553,
    "usage_percent": 2.34,
    "healthy": true
  }
}
```

### Related Documents

- `docs/FORMAL_INVARIANTS.md` - INV-LLM-S1, INV-LLM-S2
- `ARCHITECTURE_SPEC.md` - System properties section
- `SLO_SPEC.md` - SLO-5 resource efficiency
- `RUNBOOK.md` - Emergency shutdown recovery procedure

## References

- Google SRE Book, Chapter 21: "Handling Overload"
- Kubernetes Documentation: [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- MLSDM Internal: `docs/FORMAL_INVARIANTS.md`

---

*This ADR documents the rationale for CORE-04 memory bounds as part of DOC-001 from PROD_GAPS.md*
