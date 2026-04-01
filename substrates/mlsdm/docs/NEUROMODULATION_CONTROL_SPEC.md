# Neuromodulation Control Specification

**Document Version:** 1.0.0
**Status:** Draft (vNext)

## Purpose

Defines engineered neuromodulator analogs as bounded control parameters. These parameters influence exploration, learning, memory consolidation, and policy strictness without overriding governance constraints.

## Control Parameters

| Parameter | Range | Description | Decay |
| --- | --- | --- | --- |
| Exploration Bias | [0.0, 1.0] | Bias toward exploration vs. exploitation | 0.9 |
| Learning Rate | [0.001, 0.5] | Online update step size | 0.9 |
| Memory Consolidation Bias | [0.0, 1.0] | Bias toward long-term memory consolidation | 0.9 |
| Policy Strictness | [0.0, 1.0] | Tightness of policy enforcement | 0.9 |

## Dynamics

- **Decay:** new_value = current * decay + target * (1 - decay)
- **Homeostatic Brake:** if memory pressure exceeds threshold, exploration and learning rate are reduced.
- **Risk Coupling:** risk_mode increases policy strictness and reduces exploration.

## Governance Inhibition Rule (Non-Negotiable)

Neuromodulators **must not** override governance inhibition.

```
allow_execution = governance_gate(allow_execution, policy_strictness)
```

The governance gate always returns the original allow_execution flag.

## Tests

- `tests/unit/test_neuromodulation_control.py`
  - Bounds enforcement
  - Governance inhibition dominance
  - Accumulator saturation
- `tests/property/test_invariants_homeostasis.py`
  - Homeostasis invariants across random inputs

## Implementation References

- `src/mlsdm/cognition/neuromodulation.py`
- `src/mlsdm/cognition/homeostasis.py`
