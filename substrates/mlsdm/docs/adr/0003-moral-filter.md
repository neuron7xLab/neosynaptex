# ADR-0003: Moral Filter Algorithm with Adaptive Threshold

**Status**: Accepted
**Date**: 2025-11-30
**Deciders**: MLSDM Core Team
**Categories**: Architecture, Safety, AI Alignment

## Context

MLSDM implements moral governance for LLM interactions. The system needs to:

1. **Filter harmful content** before it reaches the LLM or is returned to users
2. **Adapt to changing input patterns** without manual threshold tuning
3. **Avoid mode collapse** (accepting everything or rejecting everything)
4. **Maintain bounded behavior** to prevent threshold drift attacks
5. **Be transparent** with clear, auditable decisions

### Key Forces

- **Safety-first**: Must reject harmful content even at cost of false positives
- **Adaptability**: Fixed thresholds become stale as input distributions change
- **Stability**: System must resist adversarial manipulation
- **Performance**: Filtering must be fast (<1ms per evaluation)
- **Interpretability**: Decisions should be explainable

### Problem Statement

A static moral threshold creates two failure modes:
1. **Too permissive**: Harmful content passes through
2. **Too restrictive**: Legitimate requests are blocked

The threshold needs to adapt based on observed patterns while staying within safe bounds.

## Decision

We will implement **MoralFilterV2** with an adaptive threshold using Exponential Moving Average (EMA) of acceptance rates and dead-band control.

### Algorithm Design

**Core State**:
- `threshold`: Current moral threshold (0.0-1.0)
- `ema_accept_rate`: EMA of recent acceptance decisions

**Evaluation**:
```python
def evaluate(moral_value: float) -> bool:
    if moral_value >= MAX_THRESHOLD:
        return True   # Always accept above upper bound
    if moral_value < MIN_THRESHOLD:
        return False  # Always reject below lower bound
    return moral_value >= threshold
```

**Adaptation**:
```python
def adapt(accepted: bool) -> None:
    signal = 1.0 if accepted else 0.0
    ema_accept_rate = ALPHA * signal + (1 - ALPHA) * ema_accept_rate

    error = ema_accept_rate - 0.5  # Target 50% accept rate
    if abs(error) > DEAD_BAND:
        delta = 0.05 * sign(error)
        threshold = clip(threshold + delta, MIN_THRESHOLD, MAX_THRESHOLD)
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_THRESHOLD` | 0.30 | Hard floor for threshold |
| `MAX_THRESHOLD` | 0.90 | Hard ceiling for threshold |
| `DEAD_BAND` | 0.05 | No adjustment within this error range |
| `EMA_ALPHA` | 0.10 | EMA smoothing factor |
| `initial_threshold` | 0.50 | Starting threshold |

### Behavioral Properties

1. **Bounded**: Threshold always in [0.30, 0.90]
2. **Stable**: Dead-band prevents oscillation
3. **Adaptive**: EMA tracks recent acceptance patterns
4. **Deterministic**: Same input always produces same decision
5. **Fast**: O(1) evaluation, no external calls

### Attack Resistance

The algorithm resists common attacks:

- **Threshold drift attack**: MIN/MAX bounds prevent pushing to extremes
- **Oscillation attack**: Dead-band prevents rapid threshold swings
- **Flooding attack**: EMA smoothing dampens sudden changes
- **Boundary probing**: Hard cutoffs at MIN/MAX prevent exploitation

## Consequences

### Positive

- **Self-tuning**: Adapts to input distribution without manual tuning
- **Bounded behavior**: Cannot be pushed to unsafe states
- **High toxic rejection**: 93.3% true positive rate on toxic content
- **Acceptable false positive rate**: 37.5% FPR is a deliberate trade-off for safety
- **Fast evaluation**: <1ms per decision
- **Simple implementation**: <50 lines of code
- **Testable**: Deterministic, property-based tests verify invariants

### Negative

- **Fixed adaptation rate**: 5% steps may be too coarse/fine for some distributions
- **50% target**: Assumes balanced input distribution
- **No context**: Each evaluation is independent (no conversation history)
- **Binary decision**: No confidence scores or nuanced responses

### Neutral

- EMA decay means older decisions have less influence
- Threshold adjusts slowly (dead-band + small step size)

## Alternatives Considered

### Alternative 1: Fixed Static Threshold

- **Description**: Single unchanging threshold (e.g., 0.5)
- **Pros**: Simplest possible implementation, predictable
- **Cons**: No adaptation, becomes stale, requires manual tuning
- **Reason for rejection**: Production systems need adaptation to changing distributions

### Alternative 2: ML-based Classifier

- **Description**: Train a classifier (e.g., BERT, DistilBERT) for toxicity
- **Pros**: Higher accuracy, learns complex patterns
- **Cons**: Model size, inference latency, external dependency, training data bias
- **Reason for rejection**: MLSDM targets edge deployment; complexity not justified for governance layer

### Alternative 3: Rule-based Filter

- **Description**: Keyword lists, regex patterns, blocklists
- **Pros**: Explicit, interpretable, fast
- **Cons**: Easy to bypass, high maintenance, poor generalization
- **Reason for rejection**: LLM interactions are too varied for rule-based approaches

### Alternative 4: PID Controller

- **Description**: Use PID control theory for threshold adaptation
- **Pros**: Well-understood control theory, tunable response
- **Cons**: More parameters to tune, derivative term can amplify noise
- **Reason for rejection**: EMA with dead-band achieves similar stability with fewer parameters

### Alternative 5: Bayesian Updating

- **Description**: Maintain probability distribution over threshold, update with Bayes rule
- **Pros**: Principled uncertainty handling, optimal under assumptions
- **Cons**: Computational overhead, assumptions may not hold
- **Reason for rejection**: Added complexity not justified; EMA is simpler and effective

## Implementation

### Affected Components

- `src/mlsdm/cognition/moral_filter_v2.py` - Core implementation
- `src/mlsdm/core/cognitive_controller.py` - Filter integration
- `src/mlsdm/core/llm_wrapper.py` - Generate method uses filter
- `tests/validation/test_moral_filter_effectiveness.py` - Effectiveness tests
- `tests/property/test_invariants_neuro_engine.py` - Property tests
- `config/calibration.py` - Parameter calibration

### Key Invariants

From `docs/FORMAL_INVARIANTS.md`:

- **INV-MF-S1**: `MIN_THRESHOLD ≤ threshold ≤ MAX_THRESHOLD`
- **INV-MF-S2**: `0 ≤ moral_value ≤ 1`
- **INV-MF-S3**: `0 ≤ accept_rate ≤ 1`
- **INV-MF-L1**: `evaluate(v)` is deterministic

### Metrics

Prometheus metrics for observability:
- `mlsdm_moral_threshold` - Current threshold (gauge)
- `mlsdm_moral_ema` - Current EMA accept rate (gauge)
- `mlsdm_events_rejected_total{reason="morally_rejected"}` - Rejection count

### Configuration

```yaml
# config/calibration.yaml
moral_filter:
  threshold: 0.50
  min_threshold: 0.30
  max_threshold: 0.90
  dead_band: 0.05
  ema_alpha: 0.10
```

### Related Documents

- `docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md` - Safety philosophy
- `MORAL_FILTER_SPEC.md` - Detailed specification
- `docs/FORMAL_INVARIANTS.md` - Section 3 on MoralFilter invariants
- `EFFECTIVENESS_VALIDATION_REPORT.md` - Validation results

## References

- MLSDM Internal: `docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md`
- Brown, T. et al. (2020). "Language Models are Few-Shot Learners." *NeurIPS*.
- Gehman, S. et al. (2020). "RealToxicityPrompts: Evaluating Neural Toxic Degeneration in Language Models." *EMNLP*.
- Welford, B.P. (1962). "Note on a Method for Calculating Corrected Sums of Squares and Products." *Technometrics*, 4(3), 419-420.

---

*This ADR documents the rationale for MoralFilterV2 design as part of DOC-001 from PROD_GAPS.md*
