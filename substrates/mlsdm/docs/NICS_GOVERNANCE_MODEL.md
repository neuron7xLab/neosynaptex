# Governance-as-Computation Model (NICS)

**Document Version:** 1.0.0
**Status:** Draft (Reference-Class)

## Purpose

Defines governance as a first-class computational layer that performs inhibition over the action space, not as static configuration.

## Computational Model

```
inputs + state + policy
  → inhibitory evaluation
  → allow/deny + constraints
```

### Inputs
- policy rules (versioned, auditable)
- risk contour signals
- decision trace context

### Outputs
- inhibition result (allow/deny)
- constraints (token caps, safe-response modes)
- audit tags

## Veto Power (Dominance)

Governance overrides all adaptive subsystems:

```
if governance.allow_execution is False:
    action := blocked
```

## Change Control

Governance updates require:
1. explicit intent and approval path
2. impact analysis
3. backward compatibility checks
4. versioned rollout

## Reference Implementation Hooks

- Inhibition gates in `NeuroCognitiveEngine` enforce allow/deny.
- Decision traces capture the governance result per request.
