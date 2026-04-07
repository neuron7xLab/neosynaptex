# Reproducibility Guide

> **Audience:** reviewers, replicators, and contributors who need to
> independently verify the gamma-scaling results reported in the manuscript.
>
> All results are fully reproducible from this repository. Three paths are
> described below. Start with Option A (Docker) for maximum isolation.

---

## TL;DR — One command

```bash
docker build -f Dockerfile.reproduce -t neosynaptex-repro . && docker run --rm neosynaptex-repro
```

Expected: exits 0 and prints a gamma table matching the values below.

---

## Option A: Docker (recommended)

Docker provides a fully isolated, pinned environment (Python 3.12).

### Prerequisites

- Docker installed and running
- ~2 GB disk space (image + data)

### Steps

```bash
# 1. Clone
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex

# 2. Build image
docker build -f Dockerfile.reproduce -t neosynaptex-repro .

# 3. Run reproduction
docker run --rm neosynaptex-repro
```

The entrypoint runs `reproduce.py` and:
1. Computes gamma for each substrate from scratch.
2. Compares each computed gamma against `evidence/gamma_ledger.json`.
3. Exits 0 if all values match within tolerance; exits 1 otherwise.

### Expected output (truncated)

```
Substrate            gamma  CI_low  CI_high  R2     status
zebrafish_wt         1.055  0.890   1.210    0.760  OK
eeg_physionet        1.068  0.877   1.246    -      OK
hrv_physionet        0.885  0.834   1.080    -      OK
hrv_fantasia         1.003  0.935   1.059    -      OK
gray_scott           0.979  0.880   1.010    0.995  OK
kuramoto             0.963  0.930   1.000    0.900  OK
bn_syn               0.946  0.810   1.080    0.280  OK
serotonergic_kuramoto 1.068 0.145   1.506    -      OK
cfp_diy              1.832  1.638   1.978    -      OUT-OF-REGIME (expected)

All 8 validated substrates: PASS
```

---

## Option B: Bare Python

For direct inspection without Docker.

### Prerequisites

```bash
python --version   # Python 3.10+
```

### Steps

```bash
# 1. Clone and install
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex
pip install -e ".[dev]"

# 2. Optional: empirical T1 substrates (EEG, HRV)
pip install mne wfdb specparam

# 3. Run reproduction
python reproduce.py

# 4. Run canonical gate (6 integrity checks)
python scripts/ci_canonical_gate.py

# 5. Verify manuscript claims (20 checks)
python scripts/verify_manuscript_claims.py

# 6. Run full test suite
pytest tests/ -q -m "not slow" --timeout=300
```

### Slow tests (per-substrate shuffles, ~30 min)

```bash
pytest tests/ -q -m "slow" --timeout=600
```

---

## Option C: CI

The GitHub Actions CI workflow runs the full reproduction on every push to
`main` and every pull request.

### Manually trigger CI

```bash
gh workflow run ci.yml
gh workflow run docker-reproduce.yml
```

Or push to a branch and check the Actions tab.

### CI gates

| Gate | What it checks |
|------|---------------|
| `lint` | `ruff check` + `ruff format --check` |
| `typecheck` | `mypy core/ contracts/` |
| `tests` | `pytest tests/ -q -m "not slow"` |
| `canonical_gate` | 6 integrity gates via `scripts/ci_canonical_gate.py` |
| `invariant_tests` | AXIOM_0 and all protocol invariants |
| `license_boundaries` | AGPL zone enforcement |
| `docker-reproduce` | Full Docker build and entrypoint smoke test |

All gates must pass on `main`.

---

## Interpreting Result Files

### `xform_gamma_report.json`

Human-AI cognitive substrate gamma analysis. Fields:

| Field | Type | Description |
|-------|------|-------------|
| `total_sessions` | int | Total sessions analyzed |
| `productive_sessions` | int | Sessions classified as productive |
| `gamma_all.gamma` | float | Theil-Sen gamma across all sessions |
| `gamma_all.r2` | float | R² of log-log fit |
| `gamma_all.ci_low/ci_high` | float | Bootstrap 95% CI |
| `gamma_all.verdict` | str | `METASTABLE` / `LOW_R2` / `INSUFFICIENT_DATA` |
| `gamma_productive.gamma` | float | Gamma for productive sessions only |

**Note:** `verdict = LOW_R2` means the log-log fit R² < 0.3. The gamma value
is still reported but is considered unreliable. The session substrate is
classified as T5 (exploratory) in the evidence tier system.

### `xform_proof_bundle.json`

Proof bundle from the most recent NFI integration run. Fields:

| Field | Type | Description |
|-------|------|-------------|
| `version` | str | Engine version |
| `ticks` | int | Number of observation ticks |
| `gamma.per_domain` | dict | Per-domain gamma with CI and R² |
| `gamma.mean` | float | Cross-domain mean gamma |
| `phase` | str | Phase at last tick |
| `verdict` | str | `COHERENT` / `PARTIAL` / `INCOHERENT` |
| `chain.self_hash` | str | SHA-256 of this bundle (tamper-evident) |
| `chain.prev_hash` | str | Hash of previous bundle (chain linkage) |

**Verify chain integrity:**

```python
import hashlib, json

with open("xform_proof_bundle.json") as f:
    proof = json.load(f)

clean = {k: v for k, v in proof.items() if k != "chain"}
chain = {k: v for k, v in proof["chain"].items() if k != "self_hash"}
clean["chain"] = chain
canonical = json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str)
computed = hashlib.sha256(canonical.encode()).hexdigest()
assert computed == proof["chain"]["self_hash"], "INTEGRITY FAIL"
print("Chain integrity: OK")
```

### `coherence_bridge_demo.json`

Cross-substrate coherence demonstration. Contains per-substrate phi vectors,
cross-coherence scores, and the universal scaling p-value from a multi-domain
observation run. Used as a demo artifact; not part of the canonical evidence
ledger.

### `xform_proof_bundle.json` vs `xform_combined_gamma_report.json`

- `xform_proof_bundle.json` — proof bundle from a single NFI run (chain-linked)
- `xform_combined_gamma_report.json` — combined gamma analysis across multiple
  session batches with per-batch breakdowns

---

## Expected Gamma Values per Substrate

These values are canonical. Any reproduction that deviates by more than the
listed tolerance should be investigated.

| Substrate | Expected gamma | Tolerance | Tier | Notes |
|-----------|---------------|-----------|------|-------|
| zebrafish_wt | 1.055 | ±0.05 | T1 | McGuirl 2020 data |
| eeg_physionet | 1.068 | ±0.05 | T1 | PhysioNet EEGBCI, n=20 |
| eeg_resting | 1.255 | ±0.10 | T1 | Welch PSD slope — gamma above tight window; CI=[1.032,1.452] (see note) |
| hrv_physionet | 0.885 | ±0.05 | T1 | PhysioNet NSR2DB |
| hrv_fantasia | 1.003 | ±0.05 | T1 | Fantasia dataset |
| gray_scott | 0.979 | ±0.02 | T3 | PDE simulation, F-sweep |
| kuramoto | 0.963 | ±0.02 | T3 | 128-oscillator Kc |
| bn_syn | 0.946 | ±0.10 | T3 | 1/f spiking network |
| serotonergic_kuramoto | 1.068 | ±0.20 | T5 | Wide CI expected |
| cfp_diy | 1.832 | ±0.10 | T3† | Out-of-regime control |

**Tolerance explanation:** T1 substrates use real external data with a fixed
random seed, so they should be bit-exact. The tolerance is provided for
environments where floating-point differs slightly between platforms. T3
substrates are deterministic simulations (seed=42). T5 substrates have wide
bootstrap CI by design.

**Note on `eeg_resting` (gamma = 1.255):** This substrate's point estimate is
above the [0.85, 1.15] tight metastable window. The bootstrap CI [1.032, 1.452]
does not contain 1.0. The ledger records this with `verdict: "WARNING"`. It is
still counted as a T1 evidential substrate because the measurement is real
empirical data with a valid permutation p-value (p = 0.048). The elevated gamma
may reflect the alpha-band exclusion in the Welch PSD method — see
`evidence/gamma_ledger.json::eeg_resting` for full bootstrap metadata. The
headline claim uses the wider H1 window [0.85, 1.15] with CI-containing-1.0
across the cross-substrate mean, not per-substrate point estimates.

---

## Troubleshooting Reproduction

### `ModuleNotFoundError: mne` or `wfdb`

T1 EEG and HRV substrates require optional packages:

```bash
pip install mne wfdb specparam
```

Without these, `reproduce.py` skips T1 substrates and reports `SKIPPED`.

### Gamma deviates from expected value

1. Check Python version: `python --version` (must be 3.10+)
2. Check numpy version: `python -c "import numpy; print(numpy.__version__)"`
3. Verify data files: `python scripts/ci_canonical_gate.py --gate evidence_hash`
4. Check random seed: all computations use `seed=42` — verify no global
   state modification before calling `reproduce.py`

### `scripts/ci_canonical_gate.py` fails

Run with verbose flag:

```bash
python scripts/ci_canonical_gate.py --verbose
```

Each gate reports pass/fail with the specific assertion that failed.

### Docker build fails

Common cause: network unavailable for data download during build. The
Dockerfile fetches PhysioNet data at build time. If unavailable, use the
pre-downloaded data in `data/` (already committed for T1 substrates).
