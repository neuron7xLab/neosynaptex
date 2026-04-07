# Contributing Guide

> Welcome! This guide explains how to contribute to `neosynaptex` — whether
> you are adding a new substrate adapter, fixing a bug, or improving
> documentation.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Docker (optional, for Docker reproduction)

### Clone and install

```bash
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex
pip install -e ".[dev]"
```

### Verify installation

```bash
make verify
# Should print: AXIOM_0: CONSISTENT | N substrates | gamma=0.xxxx
```

---

## Development Workflow

### Running tests

```bash
# Fast: non-slow tests only (~2-4 min)
make test
# or
pytest tests/ -q -m "not slow" --timeout=300

# Single test file
pytest tests/test_bootstrap_helpers.py -v

# Slow tests (per-substrate shuffles, ~30 min)
pytest tests/ -m "slow" --timeout=600
```

### Linting

```bash
make lint        # check only
make format      # auto-fix formatting
make typecheck   # mypy on core/ and contracts/
```

### Full verification

```bash
make verify   # lint + test + axiom consistency check
```

### Running the canonical gate

```bash
python scripts/ci_canonical_gate.py
```

Must exit 0 before any PR can be merged.

---

## Code Style

### ASCII-only identifiers (Invariant VI)

All variable names, function names, class names, and string literals used as
identifiers **must use only ASCII characters**. This is Invariant VI of the
PROTOCOL.

```python
# CORRECT
gamma_mean = compute_gamma(topo, cost)
substrate_name = "zebrafish_wt"

# WRONG (non-ASCII)
# gamma_сред = ...       # Cyrillic
# substrate_назва = ...  # mixed
```

The linter (`ruff`) enforces this on all files in `neosynaptex.py`,
`core/`, `contracts/`, `evl/`, and `tests/`.

### Other style conventions

- Maximum 4 state keys per adapter (`_MAX_STATE_KEYS = 4`).
- All float results that may be NaN must be checked before display/assertion.
- Use `np.isfinite()` rather than `!= float("nan")` for NaN checks.
- Type annotations required for all public functions and methods.
- Docstrings for all public classes and methods.

---

## Adding a New Substrate Adapter

### When is a new substrate valid?

A substrate must satisfy all of the following:

1. **CI gate:** Bootstrap 95% CI contains 1.0 (for VALIDATED status) OR
   is documented as an out-of-regime control.
2. **R2 gate:** R² >= 0.4 for the log-log fit (relaxed from 0.5, see ADR-003).
3. **Bootstrap size:** n >= 30 valid (topo, cost) pairs for CI estimation.
   Recommended n >= 100 for stable CI.
4. **Independence:** The substrate must come from a physical/biological domain
   distinct from existing substrates (no re-labelling of existing data).
5. **Surrogate test:** For T1 (empirical) substrates, must pass IAAFT surrogate
   test (p < 0.05) to rule out linear correlations.

### Substrate directory structure

```
substrates/
  my_substrate/
    __init__.py
    adapter.py        # the adapter class
    README.md         # description, data source, results
    tests/
      test_my_substrate.py
```

### Adapter template (~30 lines)

```python
"""my_substrate adapter — NeoSynaptex domain adapter.

Data source: <describe source>
Tier: T3 (simulation) / T1 (empirical) / T2 (validated simulation)
Expected gamma: <value> (CI: [<low>, <high>])
"""

from __future__ import annotations

import numpy as np


class MySubstrateAdapter:
    """Adapter for <description of physical system>.

    topo():       <what topological complexity measures here>
    thermo_cost(): <what thermodynamic cost measures here>
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0
        # Initialize internal state here

    @property
    def domain(self) -> str:
        return "my_substrate"   # ASCII only, unique

    @property
    def state_keys(self) -> list[str]:
        return ["key1", "key2"]   # 1..4 ASCII keys

    def state(self) -> dict[str, float]:
        self._t += 1
        # Compute and return current state
        return {
            "key1": float(self._compute_key1()),
            "key2": float(self._compute_key2()),
        }

    def topo(self) -> float:
        """Topological complexity C (must be > 0)."""
        return float(self._compute_topo())

    def thermo_cost(self) -> float:
        """Thermodynamic cost K (must be > 0)."""
        return float(self._compute_cost())

    def _compute_key1(self) -> float:
        raise NotImplementedError

    def _compute_key2(self) -> float:
        raise NotImplementedError

    def _compute_topo(self) -> float:
        raise NotImplementedError

    def _compute_cost(self) -> float:
        raise NotImplementedError
```

### Test template for a new substrate

```python
"""Tests for my_substrate adapter."""

import numpy as np
import pytest
from substrates.my_substrate.adapter import MySubstrateAdapter
from core.gamma import compute_gamma


def test_my_substrate_gamma_in_range():
    """gamma CI must contain 1.0 (or be documented as out-of-regime)."""
    adapter = MySubstrateAdapter(seed=42)
    topos = []
    costs = []
    for _ in range(100):
        adapter.state()
        topos.append(adapter.topo())
        costs.append(adapter.thermo_cost())

    gamma, r2, ci_lo, ci_hi, _ = compute_gamma(
        np.array(topos), np.array(costs), seed=42
    )
    assert np.isfinite(gamma), "gamma must be finite"
    assert r2 >= 0.4, f"R2={r2:.3f} below threshold 0.4"
    assert ci_lo <= 1.0 <= ci_hi, (
        f"CI=[{ci_lo:.3f}, {ci_hi:.3f}] does not contain 1.0"
    )


def test_my_substrate_state_keys():
    adapter = MySubstrateAdapter()
    state = adapter.state()
    for key in adapter.state_keys:
        assert key in state, f"Missing key {key}"
        assert np.isfinite(state[key]), f"state[{key}] is not finite"


def test_my_substrate_topo_and_cost_positive():
    adapter = MySubstrateAdapter()
    adapter.state()   # advance internal state
    assert adapter.topo() > 0
    assert adapter.thermo_cost() > 0
```

### Registering the substrate in the evidence ledger

After validating your substrate, add an entry to `evidence/gamma_ledger.json`:

```json
{
  "my_substrate": {
    "substrate": "my_substrate",
    "description": "<human-readable description>",
    "gamma": <measured value>,
    "ci_low": <bootstrap 2.5th percentile>,
    "ci_high": <bootstrap 97.5th percentile>,
    "r2": <R2 of log-log fit>,
    "n_pairs": <number of (topo, cost) pairs>,
    "p_permutation": <permutation p-value>,
    "status": "PENDING",
    "tier": "T3",
    "locked": false,
    "data_source": {"file": "path/to/data", "sha256": null},
    "adapter_code_hash": null,
    "derivation_method": "<description of derivation>",
    "method_tier": "T3"
  }
}
```

Status starts as `PENDING`. It becomes `VALIDATED` after:
- CI contains 1.0 (or is documented as out-of-regime)
- R2 >= 0.4
- At least one CI-passing test in `tests/`
- The canonical gate passes

---

## Opening a Pull Request

### Branch naming

```
feat/substrate-my-substrate
fix/gamma-bootstrap-edge-case
docs/add-operator-guide
refactor/core-gamma-cleanup
```

### PR checklist

Before opening a PR, verify:

- [ ] `make lint` exits 0
- [ ] `make test` exits 0 (`-m "not slow"`)
- [ ] `python scripts/ci_canonical_gate.py` exits 0
- [ ] No new Cyrillic or non-ASCII identifiers in code (Invariant VI)
- [ ] If adding a substrate: entry in `evidence/gamma_ledger.json`
- [ ] If changing gamma computation: update `docs/adr/` if a new decision is made
- [ ] Docstrings updated for changed public functions

### Code review process

1. Open PR against `main`.
2. CI must pass (all workflows green).
3. At least one review from a maintainer.
4. Canonical gate and manuscript claims verification must pass.
5. For new substrates: the reviewer verifies the data source and CI claim
   independently before approving.

### Merging

Squash-and-merge is the default. Each commit on `main` must be a complete,
passing unit.

---

## File Organisation

```
neosynaptex.py          # single-file engine (see ADR-001)
core/                   # reusable math: gamma, bootstrap, axioms, ...
substrates/             # one directory per substrate
tests/                  # pytest test suite
scripts/                # CI and utility scripts
evidence/               # ledger, provenance, data hashes
docs/                   # documentation (you are here)
manuscript/             # full manuscript draft
```

See [`REPO_TOPOLOGY.md`](../REPO_TOPOLOGY.md) for a complete file map.

---

## Questions

Open a GitHub Issue or start a Discussion. For security issues, see
[`substrates/hippocampal_ca1/SECURITY.md`](../substrates/hippocampal_ca1/SECURITY.md).
