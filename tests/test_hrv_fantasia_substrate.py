"""Tests for the HRV Fantasia T1 substrate.

Two classes of assertions mirror the eeg_resting test layout:

  1. **Static** — adapter protocol surface, data-hash file well-formed,
     ledger entry present. Run unconditionally.
  2. **Empirical** — actual DFA α computation on the local Fantasia
     files. Skipped gracefully when ``wfdb`` is absent or the
     PhysioNet files are not present on disk.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

from substrates.hrv_fantasia.adapter import HRVFantasiaAdapter

# ---------------------------------------------------------------------------
# Availability probes
# ---------------------------------------------------------------------------
_WFDB_AVAILABLE = importlib.util.find_spec("wfdb") is not None
_DATA_BASE = Path(__file__).parent.parent / "data" / "fantasia"
_DATA_AVAILABLE = _DATA_BASE.exists() and any(_DATA_BASE.glob("f1y*.ecg"))

_needs_wfdb = pytest.mark.skipif(
    not _WFDB_AVAILABLE, reason="wfdb not installed (optional dev dependency)"
)
_needs_data = pytest.mark.skipif(
    not _DATA_AVAILABLE, reason=f"Fantasia data not present at {_DATA_BASE}"
)


# ---------------------------------------------------------------------------
# 1. Static protocol compliance
# ---------------------------------------------------------------------------
def test_adapter_has_domain_adapter_interface():
    a = HRVFantasiaAdapter.__new__(HRVFantasiaAdapter)
    a._subj_ids = []
    a._alpha2_per_subj = []
    assert a.domain == "hrv_fantasia"
    assert "dfa_alpha2" in a.state_keys
    assert callable(HRVFantasiaAdapter.state)
    assert callable(HRVFantasiaAdapter.topo)
    assert callable(HRVFantasiaAdapter.thermo_cost)
    assert callable(HRVFantasiaAdapter.compute_gamma)


def test_fantasia_hashes_block_exists():
    path = Path(__file__).parent.parent / "evidence" / "data_hashes.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "datasets" in data
    block = data["datasets"].get("hrv_fantasia")
    assert block is not None, "missing hrv_fantasia dataset in hashes"
    assert "sha256" in block and len(block["sha256"]) >= 20
    for k, v in block["sha256"].items():
        assert len(v) == 64
        int(v, 16)
    assert "license" in block and "citation" in block


def test_hrv_fantasia_ledger_entry_present():
    path = Path(__file__).parent.parent / "evidence" / "gamma_ledger.json"
    ledger = json.loads(path.read_text())
    entry = ledger["entries"].get("hrv_fantasia")
    assert entry is not None, "ledger missing hrv_fantasia entry"
    assert 0.5 < entry["gamma"] < 2.0
    assert entry["ci_low"] < entry["gamma"] < entry["ci_high"]
    assert entry["method_tier"] == "T1"


# ---------------------------------------------------------------------------
# 2. Empirical assertions
# ---------------------------------------------------------------------------
@_needs_wfdb
@_needs_data
@pytest.mark.slow
def test_gamma_in_metastable_window():
    """Healthy young cardiac rhythm has DFA α ≈ 1 (Peng 1995)."""
    adapter = HRVFantasiaAdapter(n_subjects=10, seed=42)
    result = adapter.compute_gamma()
    gamma = result["gamma"]
    print(
        f"[hrv_fantasia] γ(α₂)={gamma:.4f} "
        f"CI95=[{result['ci_low']:.4f}, {result['ci_high']:.4f}] "
        f"n_subj={result['n_subjects']} verdict={result['verdict']}"
    )
    assert math.isfinite(gamma)
    # Generous physiological band — stricter metastable assertion follows
    assert 0.7 <= gamma <= 1.3, f"γ={gamma:.4f} leaves [0.7, 1.3] metastable window"


@_needs_wfdb
@_needs_data
@pytest.mark.slow
def test_ci_crosses_unity():
    """For a T1 cardiac witness the CI must contain 1.0 — else the
    claim 'healthy hearts are 1/f' is not supported on this cohort."""
    adapter = HRVFantasiaAdapter(n_subjects=10, seed=42)
    result = adapter.compute_gamma()
    assert result["ci_contains_unity"], (
        f"CI=[{result['ci_low']:.4f}, {result['ci_high']:.4f}] does not contain 1.0"
    )


@_needs_wfdb
@_needs_data
@pytest.mark.slow
def test_reproducibility_bitexact():
    r1 = HRVFantasiaAdapter(n_subjects=5, seed=7).compute_gamma()
    r2 = HRVFantasiaAdapter(n_subjects=5, seed=7).compute_gamma()
    assert math.isclose(r1["gamma"], r2["gamma"], abs_tol=1e-12)
    assert math.isclose(r1["ci_low"], r2["ci_low"], abs_tol=1e-12)
    assert math.isclose(r1["ci_high"], r2["ci_high"], abs_tol=1e-12)


@_needs_wfdb
@_needs_data
@pytest.mark.slow
def test_data_files_match_recorded_hashes():
    import hashlib

    path = Path(__file__).parent.parent / "evidence" / "data_hashes.json"
    block = json.loads(path.read_text())["datasets"]["hrv_fantasia"]
    repo_root = Path(__file__).parent.parent
    data_root = repo_root / "data"
    checked = 0
    for rel_path, expected in block["sha256"].items():
        full = data_root / rel_path
        if not full.exists():
            continue
        actual = hashlib.sha256(full.read_bytes()).hexdigest()
        assert actual == expected, f"hash mismatch for {rel_path}"
        checked += 1
    assert checked > 0, "no Fantasia files available to verify against hashes"
    print(f"[hrv_fantasia] verified SHA-256 for {checked} files")
