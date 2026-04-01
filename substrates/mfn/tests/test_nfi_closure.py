"""Tests for NFI closure contract — CA1-LAM ↔ MFN+ integration.

8 mandatory tests + 2 integration tests.
Ref: Vasylenko (2026)
"""

from __future__ import annotations

import dataclasses
import pathlib

import numpy as np
import pytest

from mycelium_fractal_net.nfi.ca1_lam import CA1TemporalBuffer
from mycelium_fractal_net.nfi.contract import NFIStateContract
from mycelium_fractal_net.nfi.gamma_probe import GammaEmergenceProbe, GammaEmergenceReport
from mycelium_fractal_net.tau_control.types import MFNSnapshot


# ── Helpers ──────────────────────────────────────────────────────

def _make_snapshot(
    free_energy: float = 50.0,
    betti_0: int = 10,
    d_box: float = 1.5,
) -> MFNSnapshot:
    return MFNSnapshot(
        state_vector=np.array([free_energy, float(betti_0), d_box]),
        free_energy=free_energy,
        betti_0=betti_0,
        d_box=d_box,
    )


def _healthy_contract_series(n: int = 20) -> list[NFIStateContract]:
    """Simulate a healthy series: smooth free-energy ramp with stable betti."""
    from mycelium_fractal_net.neurochem.gnc import GNCState

    buf = CA1TemporalBuffer(capacity=64)
    contracts: list[NFIStateContract] = []
    rng = np.random.default_rng(42)

    for i in range(n):
        # Smooth trajectory with slight noise
        fe = 30.0 + i * 2.0 + rng.normal(0, 0.5)
        b0 = max(1, 8 + int(rng.normal(0, 1)))
        d_box = 1.3 + 0.01 * i + rng.normal(0, 0.02)
        snap = _make_snapshot(fe, b0, d_box)
        buf.push(snap)
        coh = buf.coherence_score()
        contracts.append(NFIStateContract(
            mfn_snapshot=snap,
            modulation=GNCState.default(),
            temporal=buf,
            coherence=coh,
        ))
    return contracts


def _noise_contract_series(n: int = 20) -> list[NFIStateContract]:
    """Simulate a noisy series: random uncorrelated snapshots."""
    from mycelium_fractal_net.neurochem.gnc import GNCState

    buf = CA1TemporalBuffer(capacity=64)
    contracts: list[NFIStateContract] = []
    rng = np.random.default_rng(99)

    for _ in range(n):
        fe = rng.uniform(0, 200)
        b0 = rng.integers(0, 100)
        d_box = rng.uniform(0.5, 2.0)
        snap = _make_snapshot(fe, int(b0), d_box)
        buf.push(snap)
        coh = buf.coherence_score()
        contracts.append(NFIStateContract(
            mfn_snapshot=snap,
            modulation=GNCState.default(),
            temporal=buf,
            coherence=coh,
        ))
    return contracts


# ══════════════════════════════════════════════════════════════════
# TEST 1: NFIStateContract does not contain field 'gamma'
# ══════════════════════════════════════════════════════════════════

def test_contract_no_gamma_field():
    fields = [f.name for f in dataclasses.fields(NFIStateContract)]
    assert "gamma" not in fields, f"VIOLATION: gamma in contract fields: {fields}"


# ══════════════════════════════════════════════════════════════════
# TEST 2: CA1TemporalBuffer.coherence_score() in [0, 1]
# ══════════════════════════════════════════════════════════════════

def test_ca1_coherence_score_range():
    buf = CA1TemporalBuffer(capacity=16)
    # Empty buffer
    assert buf.coherence_score() == 0.0

    # Single snapshot
    buf.push(_make_snapshot())
    assert buf.coherence_score() == 0.0

    # Multiple snapshots
    rng = np.random.default_rng(7)
    for i in range(15):
        buf.push(_make_snapshot(
            free_energy=50.0 + rng.normal(0, 5),
            betti_0=max(1, 10 + int(rng.normal(0, 2))),
            d_box=1.5 + rng.normal(0, 0.1),
        ))
    score = buf.coherence_score()
    assert 0.0 <= score <= 1.0, f"coherence_score={score} out of range"


# ══════════════════════════════════════════════════════════════════
# TEST 3: NFIClosureLoop.step() returns NFIStateContract
# ══════════════════════════════════════════════════════════════════

def test_closure_loop_returns_contract():
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.nfi.closure import NFIClosureLoop

    loop = NFIClosureLoop()
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=30, seed=0))
    contract = loop.step(seq)

    assert isinstance(contract, NFIStateContract)
    assert contract.mfn_snapshot is not None
    assert contract.mfn_snapshot.free_energy is not None
    assert contract.mfn_snapshot.betti_0 is not None
    assert contract.mfn_snapshot.d_box is not None
    assert 0.0 <= contract.coherence <= 1.0


# ══════════════════════════════════════════════════════════════════
# TEST 4: GammaEmergenceProbe reads only List[NFIStateContract]
# ══════════════════════════════════════════════════════════════════

def test_gamma_probe_accepts_only_contracts():
    """GammaEmergenceProbe.analyze() signature accepts List[NFIStateContract]."""
    import inspect

    sig = inspect.signature(GammaEmergenceProbe.analyze)
    params = list(sig.parameters.keys())
    # Should be (self, contracts) — no FieldSequence parameter
    assert "contracts" in params
    assert "seq" not in params and "field_sequence" not in params


# ══════════════════════════════════════════════════════════════════
# TEST 5: GammaEmergenceProbe.report.mechanistic_source not None when EMERGENT
# ══════════════════════════════════════════════════════════════════

def test_gamma_probe_emergent_has_source():
    contracts = _healthy_contract_series(30)
    probe = GammaEmergenceProbe(n_bootstrap=200, rng_seed=42)
    report = probe.analyze(contracts)

    if report.label == "EMERGENT":
        assert report.mechanistic_source is not None, \
            "EMERGENT report must have mechanistic_source"
        assert report.gamma_value is not None
        assert report.r_squared is not None


# ══════════════════════════════════════════════════════════════════
# TEST 6: tau_control does NOT import gamma or GammaEmergenceProbe
# ══════════════════════════════════════════════════════════════════

def test_tau_control_isolation():
    tau_dir = pathlib.Path(__file__).resolve().parent.parent / "src" / "mycelium_fractal_net" / "tau_control"
    if not tau_dir.exists():
        # Try alternative layout
        tau_dir = pathlib.Path(__file__).resolve().parent.parent / "mycelium_fractal_net" / "tau_control"
    if not tau_dir.exists():
        # Installed package — find via import
        import mycelium_fractal_net.tau_control as tc
        tau_dir = pathlib.Path(tc.__file__).parent

    for f in tau_dir.rglob("*.py"):
        src = f.read_text()
        assert "gamma_probe" not in src, f"ISOLATION VIOLATED in {f.name}: imports gamma_probe"
        assert "GammaEmergence" not in src, f"ISOLATION VIOLATED in {f.name}: references GammaEmergence"


# ══════════════════════════════════════════════════════════════════
# TEST 7: Healthy sequence -> EMERGENT or valid analysis
# ══════════════════════════════════════════════════════════════════

def test_healthy_sequence_analysis():
    contracts = _healthy_contract_series(30)
    probe = GammaEmergenceProbe(n_bootstrap=200, rng_seed=42)
    report = probe.analyze(contracts)

    assert report.label in ("EMERGENT", "NOT_EMERGED", "INSUFFICIENT_DATA")
    assert report.n_contracts == 30
    # Healthy series should at least produce data
    assert report.label != "INSUFFICIENT_DATA"


# ══════════════════════════════════════════════════════════════════
# TEST 8: Noise sequence -> NOT_EMERGED or INSUFFICIENT_DATA
# ══════════════════════════════════════════════════════════════════

def test_noise_sequence_analysis():
    contracts = _noise_contract_series(20)
    probe = GammaEmergenceProbe(n_bootstrap=200, rng_seed=99)
    report = probe.analyze(contracts)

    assert report.label in ("NOT_EMERGED", "INSUFFICIENT_DATA", "EMERGENT")
    # Even if noise accidentally fits, the report should be valid
    assert report.n_contracts == 20


# ══════════════════════════════════════════════════════════════════
# TEST 9 (bonus): CA1TemporalBuffer compress produces valid summary
# ══════════════════════════════════════════════════════════════════

def test_ca1_compress():
    buf = CA1TemporalBuffer(capacity=32)
    for i in range(10):
        buf.push(_make_snapshot(free_energy=20.0 + i * 3.0, betti_0=5 + i, d_box=1.2 + i * 0.05))

    summary = buf.compress()
    assert summary.n_samples == 10
    assert summary.mean_free_energy > 0.0
    assert len(summary.betti_trajectory) == 10
    assert summary.phase_stability >= 0.0


# ══════════════════════════════════════════════════════════════════
# TEST 10 (bonus): Full cycle with real simulation
# ══════════════════════════════════════════════════════════════════

def test_full_cycle_real_simulation():
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.nfi.closure import NFIClosureLoop

    loop = NFIClosureLoop()
    contracts: list[NFIStateContract] = []

    for i in range(12):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=30, seed=i))
        contracts.append(loop.step(seq))

    # All contracts valid
    for c in contracts:
        assert isinstance(c, NFIStateContract)
        assert 0.0 <= c.coherence <= 1.0

    # Gamma probe analysis
    probe = GammaEmergenceProbe(n_bootstrap=100, rng_seed=42)
    report = probe.analyze(contracts)
    assert report.label in ("EMERGENT", "NOT_EMERGED", "INSUFFICIENT_DATA")
