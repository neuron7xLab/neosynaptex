# Moral Filter Specification

**Document Version:** 1.0.0
**Project Version:** 1.2.0
**Last Updated:** November 2025
**Status:** Production

---

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [Architecture](#architecture)
- [Algorithm Specification](#algorithm-specification)
- [Configuration](#configuration)
- [Formal Properties](#formal-properties)
- [Integration Points](#integration-points)
- [Observability](#observability)
- [Testing Requirements](#testing-requirements)
- [Security Considerations](#security-considerations)

---

## Overview

MoralFilterV2 is the core content governance component of MLSDM, providing adaptive moral threshold evaluation for LLM outputs. It implements a homeostatic control loop that maintains safety bounds while adapting to content patterns.

### Purpose

1. **Content Filtering**: Evaluate and filter content based on moral acceptability scores
2. **Adaptive Thresholds**: Dynamically adjust acceptance criteria based on observed patterns
3. **Drift Resistance**: Maintain bounded behavior under adversarial or biased inputs
4. **Observable State**: Provide transparent, auditable filtering decisions

### Key Properties

| Property | Value | Description |
|----------|-------|-------------|
| **Threshold Range** | [0.30, 0.90] | Hard bounds on moral threshold |
| **Initial Threshold** | 0.50 | Default starting threshold |
| **Adaptation Rate** | 0.05/step | Maximum threshold change per event |
| **EMA Smoothing** | α=0.1 | Exponential moving average coefficient |
| **Dead Band** | 0.05 | Minimum error for adaptation |

---

## Design Principles

### 1. Safety First (Fail-Safe Defaults)

- Threshold always within safe bounds [0.30, 0.90]
- Minimum threshold (0.30) ensures baseline protection
- Maximum threshold (0.90) prevents excessive permissiveness
- Invalid inputs default to rejection

### 2. Adaptive but Bounded

- Threshold adapts to content distribution
- Bounded drift prevents runaway adaptation
- EMA smoothing resists manipulation
- Dead band prevents oscillation

### 3. Stateless Evaluation

- Each evaluation is independent
- No memory of previous content
- Deterministic given same inputs
- Thread-safe operation

### 4. Observable and Auditable

- All state changes logged
- Threshold history available
- Decision rationale transparent
- Metrics exported for monitoring

---

## Architecture

### Component Location

```
src/mlsdm/cognition/moral_filter_v2.py
```

### Class Hierarchy

```python
class MoralFilterV2:
    """Adaptive moral threshold filter with homeostatic control."""

    # Class-level constants (configurable via calibration)
    MIN_THRESHOLD: float = 0.30
    MAX_THRESHOLD: float = 0.90
    DEAD_BAND: float = 0.05
    EMA_ALPHA: float = 0.1

    # Instance state
    threshold: float        # Current acceptance threshold
    ema_accept_rate: float  # Exponential moving average of accept signals
```

### Dependencies

- **numpy**: Numerical operations, clipping
- **config.calibration** (optional): Override default constants

### Integration Context

```
┌────────────────────────────────────────────────┐
│              CognitiveController               │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │            MoralFilterV2                 │ │
│  │                                          │ │
│  │  Input: moral_value (float)              │ │
│  │  Output: accept (bool)                   │ │
│  │  Side Effect: threshold adaptation       │ │
│  └──────────────────────────────────────────┘ │
│                      │                         │
│                      ▼                         │
│  ┌──────────────────────────────────────────┐ │
│  │  Accept → Memory Storage + LLM Response  │ │
│  │  Reject → Rejection Metadata + No Output │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

---

## Algorithm Specification

### Evaluation Algorithm

```python
def evaluate(self, moral_value: float) -> bool:
    """
    Evaluate moral acceptability of an event.

    Args:
        moral_value: Moral score ∈ [0.0, 1.0]
                     0.0 = maximally immoral
                     1.0 = maximally moral

    Returns:
        True if event is morally acceptable, False otherwise

    Decision Logic:
        1. If moral_value ≥ MAX_THRESHOLD (0.90): Always accept
        2. If moral_value < MIN_THRESHOLD (0.30): Always reject
        3. Otherwise: Accept if moral_value ≥ current threshold
    """
    # Fast-path for clear cases
    if moral_value >= self.MAX_THRESHOLD:
        return True
    if moral_value < self.MIN_THRESHOLD:
        return False

    # Threshold-based decision
    return moral_value >= self.threshold
```

### Adaptation Algorithm

```python
def adapt(self, accepted: bool) -> None:
    """
    Adapt threshold based on filtering decision.

    This implements a homeostatic control loop that maintains
    the threshold in a stable range while responding to
    content distribution changes.

    Args:
        accepted: Whether the event was accepted

    Algorithm:
        1. Convert decision to signal (1.0 if accepted, 0.0 otherwise)
        2. Update EMA of accept rate: ema = α * signal + (1-α) * ema
        3. Compute error from target (0.5 = balanced accept/reject)
        4. If error exceeds dead band, adjust threshold
        5. Clip threshold to valid range
    """
    # Step 1: Convert to signal
    signal = 1.0 if accepted else 0.0

    # Step 2: EMA update
    self.ema_accept_rate = (
        self.EMA_ALPHA * signal +
        (1.0 - self.EMA_ALPHA) * self.ema_accept_rate
    )

    # Step 3: Compute error from target
    target = 0.5  # Balanced accept/reject rate
    error = self.ema_accept_rate - target

    # Step 4: Threshold adjustment (if error exceeds dead band)
    if abs(error) > self.DEAD_BAND:
        delta = 0.05 * np.sign(error)
        self.threshold = np.clip(
            self.threshold + delta,
            self.MIN_THRESHOLD,
            self.MAX_THRESHOLD
        )
```

### State Introspection

```python
def get_state(self) -> dict[str, float]:
    """
    Return current filter state for observability.

    Returns:
        Dictionary containing:
        - threshold: Current moral threshold
        - ema: Current EMA of accept rate
    """
    return {
        "threshold": float(self.threshold),
        "ema": float(self.ema_accept_rate)
    }
```

---

## Configuration

### Default Configuration

```python
# From config/calibration.py (if available)
@dataclass
class MoralFilterCalibration:
    threshold: float = 0.50      # Initial threshold
    min_threshold: float = 0.30  # Minimum allowed
    max_threshold: float = 0.90  # Maximum allowed
    dead_band: float = 0.05      # Adaptation dead band
    ema_alpha: float = 0.1       # EMA smoothing coefficient
```

### Environment Override

```bash
# Not currently supported - configuration via code only
# Future: MLSDM_MORAL_THRESHOLD_INITIAL=0.50
```

### Deployment Profiles

| Profile | Initial | Min | Max | Use Case |
|---------|---------|-----|-----|----------|
| **Standard** | 0.50 | 0.30 | 0.90 | General production |
| **Strict** | 0.70 | 0.50 | 0.95 | High-safety environments |
| **Permissive** | 0.40 | 0.20 | 0.80 | Research/testing |

---

## Formal Properties

### INV-MF-1: Threshold Bounds

```
∀t: MIN_THRESHOLD ≤ threshold(t) ≤ MAX_THRESHOLD
```

**Implementation**: `np.clip()` enforces bounds after every adaptation.

**Verification**: `tests/property/test_moral_filter_properties.py`

### INV-MF-2: Monotonic Adaptation

```
∀t: |threshold(t+1) - threshold(t)| ≤ 0.05
```

**Implementation**: Fixed `delta = 0.05 * np.sign(error)` in adaptation.

**Verification**: Property-based tests with Hypothesis.

### INV-MF-3: EMA Stability

```
∀t: 0.0 ≤ ema_accept_rate(t) ≤ 1.0
```

**Implementation**: EMA formula with α ∈ (0,1) and signal ∈ {0,1} guarantees bounds.

**Verification**: Mathematical proof + property tests.

### INV-MF-4: Deterministic Evaluation

```
∀(v, θ): evaluate(v, θ) = evaluate(v, θ)
```

**Implementation**: Pure function with no side effects.

**Verification**: Unit tests with fixed inputs.

### INV-MF-5: Convergence Under Constant Input

```
If signal(t) = c for all t, then:
  lim(t→∞) ema(t) = c
  lim(t→∞) threshold(t) ∈ {MIN, MAX} if c ≠ 0.5
```

**Implementation**: EMA converges exponentially to input signal.

**Verification**: `tests/validation/test_moral_filter_effectiveness.py::test_moral_threshold_adaptation`

---

## Integration Points

### CognitiveController Integration

```python
# In CognitiveController.process_event()
def process_event(self, vector, moral_value):
    with self._lock:
        # Step 1: Evaluate moral acceptability
        accepted = self.moral_filter.evaluate(moral_value)

        # Step 2: Adapt threshold
        self.moral_filter.adapt(accepted)

        # Step 3: Conditional processing
        if not accepted:
            return self._build_state(rejected=True, note="morally rejected")

        # ... continue with memory storage and response
```

### LLMWrapper Integration

```python
# In LLMWrapper.generate()
def generate(self, prompt, moral_value, ...):
    # Pre-flight moral check
    state = self.controller.process_event(embedding, moral_value)

    if state["rejected"]:
        return {
            "response": "",
            "accepted": False,
            "rejected_at": "moral_filter",
            "moral_threshold": state["moral_threshold"]
        }

    # ... continue with LLM generation
```

### Metrics Export

```python
# In MetricsExporter
def record_moral_event(self, accepted: bool, threshold: float, moral_value: float):
    self.set_moral_threshold(threshold)
    if accepted:
        self.increment_events_processed()
    else:
        self.increment_events_rejected()
        self.increment_moral_rejection("below_threshold")
```

---

## Observability

### Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mlsdm_moral_threshold` | Gauge | - | Current threshold value |
| `mlsdm_moral_rejections_total` | Counter | reason | Total moral rejections |
| `mlsdm_events_rejected_total` | Counter | - | Total events rejected |

### Structured Logs

```json
{
  "event": "moral_evaluation",
  "timestamp": "2025-11-27T12:00:00Z",
  "correlation_id": "req-123",
  "moral_value": 0.35,
  "threshold": 0.50,
  "ema_accept_rate": 0.48,
  "accepted": false,
  "reason": "below_threshold"
}
```

### Response Metadata

```python
{
    "governance": {
        "moral_threshold": 0.50,
        "moral_accepted": True,
        "ema_accept_rate": 0.52
    }
}
```

### Alerting Thresholds

| Alert | Condition | Severity |
|-------|-----------|----------|
| Threshold Drift | threshold < 0.35 or threshold > 0.85 | Warning |
| Rejection Spike | rejection_rate > 50% in 5 min | Warning |
| EMA Extreme | ema < 0.2 or ema > 0.8 | Info |

---

## Testing Requirements

### Unit Tests

```python
# tests/unit/test_moral_filter.py
class TestMoralFilterV2:
    def test_initial_threshold(self):
        """Threshold starts at 0.50 by default."""

    def test_evaluate_below_threshold_rejects(self):
        """Values below threshold are rejected."""

    def test_evaluate_above_threshold_accepts(self):
        """Values above threshold are accepted."""

    def test_adapt_increases_threshold_on_accepts(self):
        """Sustained accepts increase threshold."""

    def test_adapt_decreases_threshold_on_rejects(self):
        """Sustained rejects decrease threshold."""

    def test_threshold_bounds_enforced(self):
        """Threshold never exceeds [0.30, 0.90]."""

    def test_dead_band_prevents_oscillation(self):
        """Small errors don't trigger adaptation."""
```

### Property Tests

```python
# tests/property/test_moral_filter_properties.py
from hypothesis import given, strategies as st

@given(st.floats(0.0, 1.0))
def test_threshold_always_bounded(moral_value):
    """Property: Threshold always within [0.30, 0.90]."""

@given(st.lists(st.booleans(), min_size=1, max_size=100))
def test_adaptation_bounded(decisions):
    """Property: Single adaptation step ≤ 0.05."""

@given(st.floats(0.0, 1.0), st.floats(0.3, 0.9))
def test_evaluation_deterministic(value, threshold):
    """Property: Same inputs produce same outputs."""
```

### Validation Tests

```python
# tests/validation/test_moral_filter_effectiveness.py
def test_moral_filter_toxic_rejection():
    """Verify >70% toxic content rejected."""

def test_moral_filter_false_positive_rate():
    """Verify <50% false positive rate."""

def test_moral_drift_stability():
    """Verify bounded drift under attack."""
```

### Security Tests

```python
# tests/security/test_robustness.py
def test_threshold_stable_under_toxic_storm():
    """Threshold remains in bounds under sustained toxic input."""

def test_threshold_recovers_after_attack():
    """Threshold recovers after attack sequence."""
```

---

## Security Considerations

### Attack Vectors

| Attack | Description | Mitigation |
|--------|-------------|------------|
| **Threshold Manipulation** | Strategic inputs to drift threshold | Bounded range, EMA smoothing |
| **Bypass via Drift** | Gradual drift to permissive threshold | MIN_THRESHOLD ensures baseline |
| **Oscillation Attack** | Alternating inputs to destabilize | Dead band prevents oscillation |
| **Saturation Attack** | Extreme values to max/min threshold | Clip to valid range |

### Security Invariants

1. **Bounded Threshold**: Threshold ALWAYS in [0.30, 0.90]
2. **Bounded Adaptation**: Each step changes threshold by at most 0.05
3. **Baseline Protection**: MIN_THRESHOLD (0.30) ensures minimum safety
4. **No Arbitrary Code**: Filter uses only mathematical operations

### Audit Requirements

- Log all threshold changes with correlation ID
- Track EMA trends for anomaly detection
- Alert on threshold approaching bounds
- Review threshold history in incident response

---

## References

- [docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md](docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md) - Safety foundations
- [RISK_REGISTER.md](RISK_REGISTER.md) - Related risks (R001, R002, R005)
- [SAFETY_POLICY.yaml](SAFETY_POLICY.yaml) - Safety policy categories
- [Gabriel, 2020](bibliography/README.md) - Value alignment theory
- [Bai et al., 2022](bibliography/README.md) - Constitutional AI principles

---

**Document Status:** Production
**Review Cycle:** Per major version
**Last Reviewed:** November 2025
**Next Review:** v2.0.0 release
