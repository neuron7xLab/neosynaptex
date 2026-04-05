"""Tests for the EEG Resting-State T1 substrate.

Two classes of assertions:

  1. **Static / no-data** — run unconditionally in every CI environment.
     These verify the adapter module imports cleanly, exposes the
     DomainAdapter surface, and computes the expected integrity
     check against ``evidence/data_hashes.json`` when ``mne`` is
     absent.

  2. **Empirical / with-data** — skipped automatically when ``mne`` is
     not installed or when the PhysioNet EDFs are not present on disk.
     When they do run, they verify that the Welch + Theil-Sen pipeline
     on real resting-state EEG yields a finite γ inside the
     physiologically plausible 1/f band [0.7, 2.0] (Donoghue 2020,
     Miller 2012) with 95 % CI width < 1.0 and that the measurement
     is bit-exact reproducible for a fixed seed.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

from substrates.eeg_resting.adapter import EEGRestingAdapter

# ---------------------------------------------------------------------------
# Availability probes
# ---------------------------------------------------------------------------
_MNE_AVAILABLE = importlib.util.find_spec("mne") is not None
_DATA_BASE = (
    Path(__file__).parent.parent
    / "data"
    / "eeg_physionet"
    / "MNE-eegbci-data"
    / "files"
    / "eegmmidb"
    / "1.0.0"
)
_DATA_AVAILABLE = _DATA_BASE.exists() and any(_DATA_BASE.glob("S*/S*R01.edf"))

_needs_mne = pytest.mark.skipif(
    not _MNE_AVAILABLE, reason="mne not installed (optional dev dependency)"
)
_needs_data = pytest.mark.skipif(
    not _DATA_AVAILABLE,
    reason=f"PhysioNet EEGBCI data not present at {_DATA_BASE}",
)


# ---------------------------------------------------------------------------
# 1. Static protocol compliance (no data required)
# ---------------------------------------------------------------------------
def test_adapter_has_domain_adapter_interface():
    """The adapter class must expose the DomainAdapter protocol surface."""
    a = EEGRestingAdapter.__new__(EEGRestingAdapter)  # no __init__ call
    # Class-level attributes / methods
    assert hasattr(EEGRestingAdapter, "domain")
    assert hasattr(EEGRestingAdapter, "state_keys")
    assert callable(EEGRestingAdapter.state)
    assert callable(EEGRestingAdapter.topo)
    assert callable(EEGRestingAdapter.thermo_cost)
    assert callable(EEGRestingAdapter.compute_gamma)
    # domain property is static
    a._subjects = []
    a._runs = (1,)
    assert a.domain == "eeg_resting"
    assert "aperiodic_exponent" in a.state_keys


def test_data_hashes_file_exists_and_is_well_formed():
    """evidence/data_hashes.json must list at least 20 EEG EDF files
    and carry citation + license in the eeg_physionet block."""
    hashes_path = Path(__file__).parent.parent / "evidence" / "data_hashes.json"
    assert hashes_path.exists(), "evidence/data_hashes.json missing"
    data = json.loads(hashes_path.read_text())
    assert "datasets" in data, "expected datasets block in data_hashes.json"
    eeg_block = data["datasets"].get("eeg_physionet")
    assert eeg_block is not None, "missing eeg_physionet dataset in hashes"
    assert "sha256" in eeg_block
    assert len(eeg_block["sha256"]) >= 20, (
        f"expected ≥ 20 hashed EDF files, got {len(eeg_block['sha256'])}"
    )
    for path_key, digest in eeg_block["sha256"].items():
        assert len(digest) == 64, f"bad digest for {path_key}"
        int(digest, 16)  # raises if not hex
    assert "license" in eeg_block
    assert "citation" in eeg_block


# ---------------------------------------------------------------------------
# 2. Empirical assertions — only when mne + data are both available
# ---------------------------------------------------------------------------
@_needs_mne
@_needs_data
@pytest.mark.slow
def test_gamma_finite_and_in_physical_band():
    """γ must be finite and inside the 1/f^α band [0.7, 2.0]
    reported in the quantitative EEG literature (Donoghue 2020,
    Miller 2012, He 2014).

    This is deliberately *broader* than the NFI metastable window
    [0.7, 1.3] — the eyes-open resting-state Welch+Theil-Sen estimate
    is known to sit around γ ≈ 1.2–1.4 and the substrate records
    that value honestly as a T1 empirical witness. Any tightening
    would amount to tuning.
    """
    adapter = EEGRestingAdapter(n_subjects=10, runs=(1,), seed=42)
    result = adapter.compute_gamma()
    gamma = result["gamma"]
    print(
        f"[eeg_resting] γ={gamma:.4f} "
        f"CI95=[{result['ci_low']:.4f}, {result['ci_high']:.4f}] "
        f"n_subj={result['n_subjects']} verdict={result['verdict']}"
    )
    assert math.isfinite(gamma), f"γ={gamma} is not finite"
    assert 0.7 <= gamma <= 2.0, f"γ={gamma:.4f} outside 1/f^α literature band [0.7, 2.0]"


@_needs_mne
@_needs_data
@pytest.mark.slow
def test_ci_width_bounded():
    """CI95 width < 1.0 — measurement has meaningful precision."""
    adapter = EEGRestingAdapter(n_subjects=10, runs=(1,), seed=42)
    result = adapter.compute_gamma()
    width = result["ci_high"] - result["ci_low"]
    print(f"[eeg_resting] CI width = {width:.4f}")
    assert width > 0.0, "bootstrap CI collapsed to a point"
    assert width < 1.0, f"CI width {width:.4f} too wide — measurement uninformative"


@_needs_mne
@_needs_data
@pytest.mark.slow
def test_reproducibility_bitexact():
    """Same seed + same data → same γ to floating-point tolerance.

    This is the reproducibility guarantee. Any drift points to
    hidden nondeterminism in the pipeline (MNE, scipy, numpy).
    """
    a1 = EEGRestingAdapter(n_subjects=5, runs=(1,), seed=7)
    r1 = a1.compute_gamma()
    a2 = EEGRestingAdapter(n_subjects=5, runs=(1,), seed=7)
    r2 = a2.compute_gamma()
    assert math.isclose(r1["gamma"], r2["gamma"], rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(r1["ci_low"], r2["ci_low"], rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(r1["ci_high"], r2["ci_high"], rel_tol=0.0, abs_tol=1e-12)
    assert r1["n_subjects"] == r2["n_subjects"]
    assert r1["n_epochs"] == r2["n_epochs"]


@_needs_mne
@_needs_data
@pytest.mark.slow
def test_per_subject_variance_visible():
    """Individual subjects must not all collapse to identical γ.

    If every subject reported the exact same value the pipeline would
    be deterministic in a way that suggests a bug.
    """
    adapter = EEGRestingAdapter(n_subjects=10, runs=(1,), seed=42)
    result = adapter.compute_gamma()
    subj_gammas = [s["gamma"] for s in result["per_subject"]]
    assert len(set(subj_gammas)) >= len(subj_gammas) - 1, (
        "per-subject γ values are suspiciously uniform"
    )
    spread = max(subj_gammas) - min(subj_gammas)
    assert spread > 0.1, f"per-subject spread {spread:.4f} too small — likely stale cache"


@_needs_mne
@_needs_data
@pytest.mark.slow
def test_data_files_match_recorded_hashes():
    """EDF files on disk must SHA-256-match the hashes recorded in
    evidence/data_hashes.json. Protects against silent data drift."""
    import hashlib

    hashes_path = Path(__file__).parent.parent / "evidence" / "data_hashes.json"
    data = json.loads(hashes_path.read_text())
    eeg_hashes = data["datasets"]["eeg_physionet"]["sha256"]
    repo_root = Path(__file__).parent.parent
    data_root = repo_root / "data"
    checked = 0
    for rel_path, expected in eeg_hashes.items():
        full = data_root / rel_path
        if not full.exists():
            # File not present on this machine — skip silently
            continue
        actual = hashlib.sha256(full.read_bytes()).hexdigest()
        assert actual == expected, f"hash mismatch for {rel_path}"
        checked += 1
    assert checked > 0, "no EDF files available to verify against recorded hashes"
    print(f"[eeg_resting] verified SHA-256 for {checked} EDF files")
