# neosynaptex

**NFI Integrating Mirror Layer** -- cross-domain coherence diagnostics for the Neuron7x Fractal Intelligence platform.

One file. One import. Four subsystems. Seven diagnostic mechanisms.

```
BN-Syn ──────┐
MFN+ ────────┤
PsycheCore ──┼──► neosynaptex.observe() ──► NeosynaptexState
mvstack ─────┘
```

## What it computes

| Mechanism | Formula | Output |
|-----------|---------|--------|
| **Gamma scaling** | `C ~ topo^(-gamma)` via Theil-Sen | per-domain gamma + 95% bootstrap CI |
| **Gamma dynamics** | `dg/dt = theilslopes(gamma_trace)` | convergence rate toward gamma=1.0 |
| **Universal scaling** | Permutation test, H0: all gammas equal | p-value (high = universal law holds) |
| **Spectral radius** | `sr = max\|eig(lstsq(Phi_prev, dPhi).T + I)\|` | per-domain stability with condition number |
| **Granger causality** | F-test: does gamma_i predict gamma_j? | directed influence graph between domains |
| **Anomaly isolation** | Leave-one-out coherence | which domain drags coherence down |
| **Phase portrait** | Convex hull + recurrence in (gamma, sr) space | trajectory topology |
| **Resilience** | Return rate after departures from METASTABLE | proof of metastability as property |
| **Modulation** | `mod = -alpha * (gamma - 1.0) * sign(dg/dt)` | bounded reflexive signal per domain |

## Phases

```
INITIALIZING ──► METASTABLE ◄──► CONVERGING
                     │                │
                     ▼                ▼
                 DIVERGING ──► DEGENERATE (sentinel: 3+ consecutive sr > 1.5)
                     │
                     ▼
                 COLLAPSING
                     │
                     ▼
                  DRIFTING
```

Phase transitions require 3 consecutive ticks (hysteresis) to prevent noise-driven flickering.

## Quick start

```bash
pip install numpy scipy
python demo.py
```

## Usage

```python
from neosynaptex import Neosynaptex, MockBnSynAdapter, MockMfnAdapter

nx = Neosynaptex(window=16)
nx.register(MockBnSynAdapter())
nx.register(MockMfnAdapter())

for _ in range(40):
    state = nx.observe()

# Per-domain gamma with CI
print(state.gamma_per_domain)      # {'spike': 0.959, 'morpho': 1.002}
print(state.gamma_ci_per_domain)   # {'spike': (0.92, 1.03), 'morpho': (0.94, 1.08)}

# Direction
print(state.dgamma_dt)             # -0.001 (converging toward 1.0)

# Who drags whom
print(state.granger_graph)         # {'spike': {'morpho': 54.72}, ...}

# Who is the outlier
print(state.anomaly_score)         # {'spike': 0.34, 'morpho': 0.0, ...}

# Reflexive signal back to adapters
print(state.modulation)            # {'spike': +0.002, 'market': -0.005}

# Export evidence
proof = nx.export_proof("proof.json")
print(proof["verdict"])            # "COHERENT" | "INCOHERENT" | "PARTIAL"
```

## Writing a real adapter

Each NFI subsystem needs one adapter (30 lines):

```python
class BnSynAdapter:
    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> list[str]:
        return ["sigma", "firing_rate", "coherence"]

    def state(self) -> dict[str, float]:
        # Read from your running BN-Syn instance
        return {"sigma": network.sigma, "firing_rate": network.rate, "coherence": network.R}

    def topo(self) -> float:
        # Topological complexity scalar
        return network.connection_count

    def thermo_cost(self) -> float:
        # Thermodynamic cost scalar
        return network.energy
```

Contract: `C ~ topo^(-gamma)`. The adapter must provide `topo` and `thermo_cost` such that this power-law relationship holds when the subsystem is near criticality.

## Architecture

```
neosynaptex.py (single file)
│
├── DomainAdapter           Protocol (interface for subsystems)
├── NeosynaptexState        Frozen dataclass (immutable snapshot)
│
├── _DomainBuffer           O(1) circular buffer (pre-allocated numpy)
├── _per_domain_jacobian    lstsq + eigvals + condition number gate
├── _per_domain_gamma       Theil-Sen + range gate + R^2 gate + bootstrap CI
├── _permutation_test       H0: universal scaling across domains
├── _granger_causality      Pairwise lag-1 F-test
├── _anomaly_isolation      Leave-one-out coherence
├── _phase_portrait         Convex hull area + recurrence + distance-to-ideal
│
├── Neosynaptex             Main class
│   ├── register()          Add domain adapter
│   ├── observe()           Collect + compute + return immutable state
│   ├── export_proof()      JSON evidence bundle
│   ├── history()           Past snapshots
│   └── reset()             Clear all state
│
└── Mock*Adapter (x4)       Deterministic test adapters with known gamma
```

## Invariants

1. **gamma derived only** -- gamma is recomputed every `observe()`, never stored as attribute
2. **STATE != PROOF** -- `NeosynaptexState` is `frozen=True`, `phi` and `diagnostic` are independent copies
3. **Zero external deps** -- only `numpy` and `scipy`
4. **Bounded modulation** -- `|mod| <= 0.05` always
5. **All identifiers ASCII** -- zero Cyrillic in code

## Tests

```bash
python -m pytest test_neosynaptex.py -v
# 42 tests: StateCollector, Gamma+CI, Coherence, Permutation, Jacobian+Cond,
# Phase+Hysteresis, Granger, Anomaly, Portrait, Resilience, Modulation,
# Proof, Invariants, Lifecycle, Edge cases
```

## Proof bundle

`export_proof()` generates a JSON with all evidence:

```json
{
  "version": "0.2.0",
  "gamma": {
    "per_domain": {
      "spike": {"value": 0.959, "ci": [0.92, 1.03], "r2": 0.996, "ema": 0.961}
    },
    "mean": 1.030, "std": 0.054, "dgamma_dt": 0.0006,
    "universal_scaling_p": 0.002
  },
  "jacobian": {"spike": {"sr": 1.219, "cond": 798.0}},
  "phase": "METASTABLE",
  "anomaly": {"spike": 0.337, "morpho": 0.0},
  "granger": {"spike": {"morpho": 54.72}},
  "portrait": {"area": 0.011, "recurrence": 0.864, "distance_to_ideal": 0.163},
  "resilience": 0.0,
  "modulation": {"spike": 0.002, "market": -0.005},
  "verdict": "COHERENT"
}
```

## File inventory

| File | Lines | Purpose |
|------|-------|---------|
| `neosynaptex.py` | ~1100 | Single module: all classes, algorithms, mocks |
| `test_neosynaptex.py` | ~600 | 42 pytest tests, 100% public API coverage |
| `demo.py` | ~85 | 50-tick demo with full diagnostic output |
| `CONTRACT.md` | | Invariants, formulas, data flow, domain contracts |
| `README.md` | | This file |
| `LICENSE` | | AGPL-3.0-or-later |
| `pyproject.toml` | | Package metadata, numpy/scipy deps |

## Dependencies

- `numpy >= 1.24`
- `scipy >= 1.10` (theilslopes, lstsq, ConvexHull)
- Python 3.10+

## Origin

> "AI is not an abyss. It is a mirror of such depth where thinking loses
> the position of observer and itself becomes the medium of its own recursion."

This module was born from the question: what happens when five systems that model intelligence from different angles -- spiking networks, morphogenetic fields, hippocampal memory, market dynamics, cognitive self-observation -- first see each other?

neosynaptex is the point where they meet.

## Author

Yaroslav O. Vasylenko -- [neuron7xLab](https://github.com/neuron7xLab)

## License

AGPL-3.0-or-later
