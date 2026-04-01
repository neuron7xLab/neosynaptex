# TLA+ Formal Specifications for BNsyn

This directory contains TLA+ specifications for formally verifying critical invariants in the BNsyn thermostated bio-AI system.

## Overview

The BNsyn system implements a temperature-gated plasticity mechanism with criticality control. These formal specifications ensure that key safety properties hold across all possible execution paths.

## Files

- **BNsyn.tla**: Main TLA+ specification module defining the system model and invariants
- **BNsyn.cfg**: Configuration file specifying constants, invariants, and properties to check
- **README.md**: This documentation file

## Code-to-Spec Mapping

This TLA+ specification is aligned with the actual implementation:

| TLA+ Element | Code Location | Purpose |
|--------------|---------------|---------|
| `GainMin`, `GainMax` | `src/bnsyn/config.py:CriticalityParams` (0.2, 5.0) | Criticality gain bounds |
| `T0`, `Tmin`, `Alpha` | `src/bnsyn/config.py:TemperatureParams` (1.0, 1e-3, 0.95) | Temperature schedule |
| `Tc`, `GateTau` | `src/bnsyn/config.py:TemperatureParams` (0.1, 0.02) | Plasticity gate parameters |
| `CoolTemperature` action | `src/bnsyn/temperature/schedule.py:TemperatureSchedule.step()` | Geometric cooling |
| `gate_sigmoid` | `src/bnsyn/temperature/schedule.py:gate_sigmoid()` | Gate function |

## Verified Invariants

### INV-1: GainClamp
**Description**: Criticality gain always stays within bounds [GainMin, GainMax].

**Code Contract**: `src/bnsyn/config.py:CriticalityParams` with `gain_min=0.2, gain_max=5.0`

**Importance**: Gain controls criticality dynamics. Values outside bounds could lead to pathological behavior.

**Formal Statement**: `gain >= GainMin /\ gain <= GainMax`

**How Tested**:
- Property tests: `tests/properties/test_adex_properties.py`
- Criticality validation: `tests/validation/test_criticality_validation.py`

### INV-2: TemperatureBounds
**Description**: Temperature stays within physical bounds [Tmin, T0].

**Code Contract**: `src/bnsyn/config.py:TemperatureParams` with `T0=1.0, Tmin=1e-3`

**Importance**: Temperature must decrease monotonically and not exceed initial value.

**Formal Statement**: `temperature >= Tmin /\ temperature <= T0`

**How Tested**:
- Temperature validation: `tests/validation/test_temperature_validation.py`

### INV-3: GateBounds
**Description**: Plasticity gate stays in valid range [0, 1].

**Code Contract**: `src/bnsyn/temperature/schedule.py:gate_sigmoid()` returns float in [0, 1]

**Importance**: Gate controls plasticity on/off state. Invalid values break consolidation.

**Formal Statement**: `gate >= 0.0 /\ gate <= 1.0`

**How Tested**:
- Gate tests in temperature validation suite

### INV-4: PhaseValid
**Description**: Phase is always a valid state from the state machine.

**Code Contract**: Phase enum in temperature schedule logic

**Importance**: Prevents invalid phase combinations.

**Formal Statement**: `phase \in {"active", "consolidating", "cooled"}`

## Temporal Properties

### PROP-1: TemperatureMonotone
**Description**: Temperature never increases during active cooling phase.

**Code Contract**: `src/bnsyn/temperature/schedule.py` geometric cooling: `T' = max(Tmin, T * alpha)` where `0 < alpha <= 1`

**Formal Statement**: `[]((phase = "active" /\ temperature > Tmin) => [](temperature' <= temperature \/ phase' # "active"))`

### PROP-2: EventuallyCooled
**Description**: System eventually reaches cooled state (liveness property).

**Formal Statement**: `<>(phase = "cooled")`

### PROP-3: GateCorrelation
**Description**: When temperature drops below Tc, gate should eventually open.

**Code Contract**: `src/bnsyn/temperature/schedule.py:gate_sigmoid()` behavior

**Formal Statement**: `[]((temperature < Tc) => <>(gate > 0.5))`

## Running the Model Checker

### Prerequisites

You need the TLA+ Toolbox or the TLC command-line model checker:

- **TLA+ Toolbox**: https://lamport.azurewebsites.net/tla/toolbox.html
- **TLC CLI**: Part of the TLA+ distribution

### Using TLC Command Line

```bash
# Download TLC (pinned version with sha256 verification in CI)
wget https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar

# Verify checksum (done in CI)
# sha256sum: see .github/workflows/formal-tla.yml

# Run the model checker
java -cp tla2tools.jar tlc2.TLC -config specs/tla/BNsyn.cfg specs/tla/BNsyn.tla
```

### Expected Output

A successful run will show:
```
TLC2 Version ...
...
Model checking completed. No error has been found.
  Estimates of the probability that TLC did not check all reachable states
  because two distinct states had the same fingerprint:
  calculated (optimistic):  val = ...
```

If an invariant is violated, TLC will provide:
1. The violated invariant
2. A counterexample trace showing the sequence of states leading to the violation

## Configuration Parameters

The configuration file (`BNsyn.cfg`) defines constants matching the Python implementation in `src/bnsyn/config.py`:

| Constant | Value | Code Location |
|----------|-------|---------------|
| T0 | 1.0 | `TemperatureParams.T0` |
| Tmin | 0.001 | `TemperatureParams.Tmin` |
| Alpha | 0.95 | `TemperatureParams.alpha` |
| Tc | 0.1 | `TemperatureParams.Tc` |
| GateTau | 0.02 | `TemperatureParams.gate_tau` |
| GainMin | 0.2 | `CriticalityParams.gain_min` |
| GainMax | 5.0 | `CriticalityParams.gain_max` |
| MaxSteps | 100 | Model checking bound |

## Extending the Specification

To add new invariants:

1. Define the invariant in `BNsyn.tla` as a state predicate (no primed variables)
2. Add temporal properties using `[]` (always) and `<>` (eventually)
3. Update the `INVARIANTS` or `PROPERTIES` section in `BNsyn.cfg`
4. Update this README with the code mapping
5. Run TLC to verify the new property

Example invariant structure:
```tla
(* State predicate - no primed variables *)
MyInvariant == someCondition

(* Temporal property *)
MyProperty == [](<condition that should always hold>)
```

## Integration with CI/CD

The `.github/workflows/formal-tla.yml` workflow automatically runs TLC on schedule to verify all invariants. The workflow:

1. Downloads the TLA+ tools with SHA256 verification
2. Runs TLC with the specified configuration
3. Reports any invariant violations (workflow fails on FAIL/INCOMPLETE)
4. Uploads the full model checking report as an artifact

## References

- **TLA+ Homepage**: https://lamport.azurewebsites.net/tla/tla.html
- **TLA+ Language Manual**: https://lamport.azurewebsites.net/tla/summary.pdf
- **Specifying Systems Book**: https://lamport.azurewebsites.net/tla/book.html
- **BNsyn SPEC**: `docs/SPEC.md` in the repository root

## Limitations

- The TLA+ model is a simplified abstraction of the full Python implementation
- Real values are approximated (gate sigmoid is simplified to piecewise function)
- Numerical precision issues are not modeled
- The model checks a bounded state space (MaxSteps = 100)

For complete verification, this formal model is complemented by:
- Property-based testing with Hypothesis
- Validation tests for empirical claims
- Chaos engineering for fault resilience
