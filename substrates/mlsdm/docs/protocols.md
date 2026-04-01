# Neuro-signal Protocols

## Protocol purpose
Neuro-signal protocols define lightweight, stable contracts for cross-module signaling in the
cognitive engine. They standardize how risk, gating, latency, and prediction-error signals are
shared across core orchestration, policy, and observability layers so that adapters can expose
consistent interfaces without importing internal implementation details.

## Neuro-signal interfaces
The protocol models are defined in `mlsdm.protocols.neuro_signals` and include:

- `RiskSignal`: normalized risk and threat scores with source metadata.
- `ActionGatingSignal`: allow/deny decision output with mode and reason metadata.
- `RewardPredictionErrorSignal`: reward prediction error deltas and derived metrics.
- `LatencyRequirement` / `LatencyProfile`: latency budgets for pipeline stages.
- `LifecycleHook`: lifecycle hook descriptors for instrumentation.
- `StabilityMetrics`: system stability indicators used for monitoring.

These dataclasses are frozen to preserve signal integrity at the API boundary.

## Adapter responsibilities
Adapters translate subsystem-specific data into protocol signals. For example:

- `RiskContractAdapter` converts `RiskInputSignals` and `RiskAssessment` results into
  `RiskSignal` and `ActionGatingSignal` outputs.
- Adapters must enforce source naming, normalize scores, and attach metadata that allows
  observability tooling to trace the origin of a signal.

## Usage examples

```python
from mlsdm.protocols.neuro_signals import RiskSignal
from mlsdm.risk.safety_control import RiskContractAdapter, RiskInputSignals

signals = RiskInputSignals(
    security_flags=("policy_violation",),
    cognition_risk_score=0.2,
    observability_anomaly_score=0.8,
)

risk_signal = RiskContractAdapter.risk_signal(signals)
assert isinstance(risk_signal, RiskSignal)
```

```python
from mlsdm.risk.safety_control import (
    RiskAssessment,
    RiskContractAdapter,
    RiskDirective,
    RiskMode,
)

gating_signal = RiskContractAdapter.action_gating_signal(
    RiskAssessment(composite_score=0.8, mode=RiskMode.DEGRADED, reasons=(), evidence={}),
    RiskDirective(
        mode=RiskMode.DEGRADED,
        allow_execution=True,
        degrade_actions=("token_cap",),
        emergency_fallback=None,
        audit_tags=("risk_degraded",),
    ),
)
assert gating_signal.mode == "degraded"
```

## Failure modes
- **Schema drift:** Modifying protocol fields without a contract review will break adapters and
  downstream observability tooling.
- **Missing metadata:** Omitting source or context metadata reduces auditability of risk and
  safety decisions.
- **Inconsistent normalization:** Adapters that fail to normalize risk or latency scores can
  produce unstable gating decisions.
- **Mutable payload misuse:** Mutating metadata after emission can invalidate audit trails; treat
  emitted signals as immutable.
