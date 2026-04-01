# Decision Trace Specification

**Document Version:** 1.0.0
**Status:** Draft (vNext)

## Purpose

The Decision Trace artifact provides a deterministic audit trail for every decision, including rejections. It captures the full chain:

```
input → memory → prediction_error → neuromodulation → governance → action
```

## Schema (JSON)

```json
{
  "trace_id": "uuid",
  "timestamp": "RFC3339",
  "input": {
    "prompt_length": 0,
    "user_intent": "string",
    "moral_value": 0.0,
    "context_top_k": 0
  },
  "memory": {
    "context_items": 0,
    "stateless_mode": false,
    "memory_pressure": 0.0
  },
  "prediction_error": {
    "perception_error": 0.0,
    "memory_error": 0.0,
    "policy_error": 0.0,
    "total_error": 0.0,
    "propagation": {
      "L1_to_L2": 0.0,
      "L2_to_L3": 0.0,
      "L1_to_L3": 0.0,
      "policy_gate": 0.0
    },
    "accumulator": {
      "cumulative_error": 0.0,
      "saturated": false
    }
  },
  "neuromodulation": {
    "state": {
      "exploration_bias": 0.0,
      "learning_rate": 0.0,
      "memory_consolidation_bias": 0.0,
      "policy_strictness": 0.0
    },
    "bounds": {
      "exploration": [0.0, 1.0],
      "learning_rate": [0.001, 0.5],
      "memory_consolidation": [0.0, 1.0],
      "policy_strictness": [0.0, 1.0]
    }
  },
  "policy": {
    "governance_gate": {
      "allow_execution": true,
      "policy_strictness": 0.0,
      "governance_locked": false
    },
    "risk_mode": "normal",
    "degrade_actions": []
  },
  "action": {
    "type": "responded",
    "response_length": 0,
    "rejected_at": null
  }
}
```

## Implementation References

- `src/mlsdm/observability/decision_trace.py`
- `src/mlsdm/engine/neuro_cognitive_engine.py`
