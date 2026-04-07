# Operator Guide

> **Audience:** engineers and researchers who need to run, monitor, and debug
> the NeoSynaptex diagnostic engine in development or CI environments.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex
pip install -e ".[dev]"

# 2. Verify installation
python -c "import neosynaptex; print(neosynaptex.__version__)"

# 3. Run all tests
pytest tests/ -q --timeout=300

# 4. Reproduce the gamma table
python reproduce.py

# 5. Run the canonical gate
python scripts/ci_canonical_gate.py
```

---

## Running the Engine

### Minimal two-domain example

```python
from neosynaptex import Neosynaptex, MockBnSynAdapter, MockMfnAdapter

nx = Neosynaptex(window=16)
nx.register(MockBnSynAdapter())
nx.register(MockMfnAdapter())

for _ in range(32):          # warm-up: need >= window ticks
    state = nx.observe()

print(f"phase        : {state.phase}")
print(f"gamma_mean   : {state.gamma_mean:.4f}")
print(f"coherence    : {state.cross_coherence:.4f}")
print(f"resilience   : {state.resilience_score:.4f}")
```

Expected output after warm-up:

```
phase        : METASTABLE
gamma_mean   : 0.9xxx
coherence    : 0.9xxx
resilience   : nan   # no departures yet
```

### Export proof bundle

```python
proof = nx.export_proof(path="proof_bundle.json")
print(proof["verdict"])   # COHERENT / PARTIAL / INCOHERENT
```

### Using real substrate adapters

```python
from substrates.zebrafish.adapter import ZebrafishAdapter
from substrates.gray_scott.adapter import GrayScottAdapter

nx = Neosynaptex(window=32)
nx.register(ZebrafishAdapter())
nx.register(GrayScottAdapter())
```

---

## Make Targets

| Target | Description |
|--------|-------------|
| `make install` | `pip install -e ".[dev]"` |
| `make test` | Run full test suite with verbose output |
| `make lint` | `ruff check` + `ruff format --check` |
| `make format` | Auto-format with ruff |
| `make typecheck` | `mypy core/ contracts/` |
| `make verify` | lint + test + axiom consistency check |
| `make demo` | Print gamma table for all substrates |
| `make report` | Print NFI state summary |
| `make reproduce` | Run `scripts/reproduce.py` |
| `make clean` | Remove `__pycache__` and `.pyc` files |

---

## Monitoring

### Key metrics to watch

| Metric | Healthy range | Action if outside |
|--------|--------------|-------------------|
| `gamma_mean` | [0.85, 1.15] | Check adapter topo/cost functions |
| `cross_coherence` | > 0.85 for COHERENT verdict | Check for outlier domain |
| `spectral_radius` | [0.80, 1.25] | DEGENERATE if >= 1.5 for 3 ticks |
| `resilience_score` | > 0.7 | Low = system not recovering from perturbations |
| `universal_scaling_p` | > 0.05 | p < 0.05 = substrates diverging |
| `anomaly_score[d]` | < 0.3 | High = domain d is outlier |

### Logging

The engine uses Python's standard `logging` module under the logger name
`neosynaptex`. To enable debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Log entries include: tick number, per-domain gamma, spectral radius, phase
transitions, and any NaN/degenerate conditions.

### Proof chain verification

Each call to `export_proof()` appends a hash-linked entry. To verify chain
integrity:

```python
import hashlib, json

with open("proof_bundle.json") as f:
    proof = json.load(f)

# Recompute hash excluding self_hash
clean = {k: v for k, v in proof.items() if k != "chain"}
chain_without_self = {k: v for k, v in proof["chain"].items() if k != "self_hash"}
clean["chain"] = chain_without_self
canonical = json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str)
computed = hashlib.sha256(canonical.encode()).hexdigest()

assert computed == proof["chain"]["self_hash"], "Chain integrity FAILED"
print("Chain integrity OK")
```

---

## Debugging Common Issues

### `RuntimeError: No adapters registered`

You called `observe()` before `register()`. Register at least one adapter first.

### `ValueError: window must be >= 8`

The `window` parameter to `Neosynaptex()` must be at least 8. Default is 16.

### `gamma_mean = NaN` after many ticks

Possible causes:
1. Adapter returns constant `topo()` or `thermo_cost()` — no variance, no fit.
2. Less than 5 valid pairs in the window (check `_MIN_PAIRS_GAMMA = 5`).
3. All log(topo) or log(cost) values are identical — Theil-Sen returns NaN.

Debug: print `buf.topos()` and `buf.costs()` for the affected domain.

### Phase stuck in `INITIALIZING`

Requires `window` ticks before Jacobian can be estimated. Default window = 16,
so call `observe()` at least 16 times.

### `phase = DEGENERATE` unexpectedly

Check `spectral_radius`. If `rho >= 1.5` for 3 consecutive ticks, the circuit
breaker fires. Usually indicates adapter `state()` values are diverging —
check for unbounded growth in the returned state dict values.

### CI failures: `canonical gate: FAIL`

Run `python scripts/ci_canonical_gate.py --verbose` to see which of the 6
gates failed. Common causes:
- `gamma_provenance`: ledger entry missing or hash mismatch
- `testpath_hermetic`: test file references data outside `data/`
- `math_core_tested`: a `core/*.py` function has no test

### Condition number warning (`cond > 1e6`)

The Jacobian estimation is numerically ill-conditioned. This happens when
state variables are nearly collinear. Increase `window` or diversify the
state keys returned by the adapter.

---

## Environment and Dependencies

### Python version

Requires Python 3.10+. CI runs on Python 3.12.

### Required packages

Installed automatically by `pip install -e ".[dev]"`:

- `numpy` — numerical core
- `scipy` — Theil-Sen, ConvexHull, lstsq
- `pytest`, `pytest-timeout` — testing

### Optional packages (T1 empirical substrates)

```bash
pip install mne wfdb specparam
```

Required only for EEG PhysioNet and HRV substrates.

### Docker reproduction

```bash
docker build -f Dockerfile.reproduce -t neosynaptex-repro .
docker run --rm neosynaptex-repro
```

The image pins Python 3.12 and all dependencies. The entrypoint runs
`reproduce.py` and exits 0 if all gamma values match the ledger.

---

## CI / Workflow Overview

| Workflow | Trigger | What it checks |
|----------|---------|---------------|
| `ci.yml` | push, PR | lint, mypy, tests, canonical gate, invariants, coverage |
| `docker-reproduce.yml` | push (relevant files) | Docker image builds and gamma reproduces |
| `.pre-commit-config.yaml` | local commit | mirrors CI lint/format gates |

All three must pass on a clean checkout of `main`.
