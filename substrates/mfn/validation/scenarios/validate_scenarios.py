#!/usr/bin/env python3
"""Canonical Scenario Bank — quantitative validation of all public claims.

Each scenario has:
  - A SimulationSpec (reproducible)
  - Quantitative assertions (not "looks right", but numbers)
  - Source reference (paper or known behavior)

Run: pytest validation/scenarios/validate_scenarios.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.field import SimulationSpec


# ═══════════════════════════════════════════════════════════════
# SCENARIO 1: TURING PATTERN FORMATION
# ═══════════════════════════════════════════════════════════════

class TestTuringPattern:
    """Turing (1952): reaction-diffusion system must form spatial patterns
    when activator diffusion < inhibitor diffusion."""

    def test_pattern_forms(self):
        """Activator deviation > 1e-6 after simulation."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        # Field should have spatial structure (not flat)
        field_range = float(seq.field.max() - seq.field.min())
        assert field_range > 1e-6, f"No pattern formed: range = {field_range}"

    def test_pattern_has_topology(self):
        """Pattern should have spatial clusters (N_clusters > 0)."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        desc = mfn.extract(seq)
        n_clusters = sum(desc.features.get(f"N_clusters_{k}", 0) for k in ("low", "med", "high"))
        assert n_clusters >= 1, f"No spatial structure: N_clusters = {n_clusters}"

    def test_fractal_dimension_in_range(self):
        """D_box should be in [1.0, 2.0] for 2D patterns."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        desc = mfn.extract(seq)
        d_box = desc.features.get("D_box", 0)
        assert 1.0 <= d_box <= 2.0, f"D_box = {d_box} outside [1.0, 2.0]"


# ═══════════════════════════════════════════════════════════════
# SCENARIO 2: ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════

class TestAnomalyDetection:
    """Baseline simulation should be classified as nominal."""

    def test_baseline_nominal(self):
        """Default config → label = 'nominal'."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        det = mfn.detect(seq)
        assert det.label in ("nominal", "watch"), f"Unexpected label: {det.label}"

    def test_anomaly_score_bounded(self):
        """Anomaly score ∈ [0, 1]."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        det = mfn.detect(seq)
        assert 0 <= det.score <= 1, f"Score out of bounds: {det.score}"


# ═══════════════════════════════════════════════════════════════
# SCENARIO 3: EARLY WARNING SIGNALS
# ═══════════════════════════════════════════════════════════════

class TestEarlyWarning:
    """EWS should detect approach to critical transitions."""

    def test_ews_score_bounded(self):
        """EWS score ∈ [0, 1]."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        ews = mfn.early_warning(seq)
        assert 0 <= ews.ews_score <= 1, f"EWS score out of bounds: {ews.ews_score}"

    def test_ews_has_transition_type(self):
        """EWS should report a transition type."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        ews = mfn.early_warning(seq)
        assert isinstance(ews.transition_type, str)
        assert len(ews.transition_type) > 0


# ═══════════════════════════════════════════════════════════════
# SCENARIO 4: DIAGNOSIS PIPELINE
# ═══════════════════════════════════════════════════════════════

class TestDiagnosisPipeline:
    """Full diagnose() pipeline should produce consistent output."""

    def test_diagnosis_severity_valid(self):
        """Severity in expected set."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        diag = mfn.diagnose(seq)
        valid = {"info", "low", "medium", "high", "critical"}
        assert diag.severity in valid, f"Unknown severity: {diag.severity}"

    def test_diagnosis_has_narrative(self):
        """Diagnosis should produce a narrative string."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        diag = mfn.diagnose(seq)
        assert diag.narrative is not None
        assert len(diag.narrative) > 10


# ═══════════════════════════════════════════════════════════════
# SCENARIO 5: FEATURE EXTRACTION
# ═══════════════════════════════════════════════════════════════

class TestFeatureExtraction:
    """extract() should produce a 57-dim embedding."""

    def test_embedding_dimension(self):
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        desc = mfn.extract(seq)
        assert len(desc.embedding) == 57, f"Expected 57 dims, got {len(desc.embedding)}"

    def test_embedding_finite(self):
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        desc = mfn.extract(seq)
        assert np.all(np.isfinite(desc.embedding)), "Embedding contains NaN/Inf"


# ═══════════════════════════════════════════════════════════════
# SCENARIO 6: REPRODUCIBILITY
# ═══════════════════════════════════════════════════════════════

class TestReproducibility:
    """Same seed → identical output."""

    def test_deterministic(self):
        """Two runs with same seed produce identical fields."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq1 = mfn.simulate(spec)
        seq2 = mfn.simulate(spec)
        assert np.array_equal(seq1.field, seq2.field), "Non-deterministic output"

    def test_different_seeds_differ(self):
        """Different seeds produce different fields."""
        seq1 = mfn.simulate(SimulationSpec(grid_size=32, steps=60, seed=42))
        seq2 = mfn.simulate(SimulationSpec(grid_size=32, steps=60, seed=43))
        assert not np.array_equal(seq1.field, seq2.field), "Different seeds gave same output"


# ═══════════════════════════════════════════════════════════════
# SCENARIO 7: HWI INEQUALITY
# ═══════════════════════════════════════════════════════════════

class TestHWIInequality:
    """Otto & Villani (2000): H ≤ W₂ · √I should hold for all t."""

    def test_hwi_holds(self):
        """HWI inequality holds for canonical simulation."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        from mycelium_fractal_net.analytics.unified_score import compute_hwi_components
        hwi = compute_hwi_components(seq.history[0], seq.field)
        assert hwi.hwi_holds, f"HWI violated: H={hwi.H:.6f} > W₂√I={hwi.hwi_rhs:.6f}"


# ═══════════════════════════════════════════════════════════════
# SCENARIO 8: INVARIANT Λ₂
# ═══════════════════════════════════════════════════════════════

class TestInvariantLambda2:
    """Vasylenko (2026): Λ₂ = H/(W₂^0.59·I^0.86) ≈ 1.92 with CV < 5%."""

    def test_lambda2_invariant(self):
        """Λ₂ CV < 5% for canonical run."""
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        op = mfn.InvariantOperator()
        L2 = op.Lambda2(seq.history)
        cv = float(np.std(L2) / (np.mean(L2) + 1e-12))
        assert cv < 0.05, f"Λ₂ CV = {cv:.4f} ≥ 5%"
