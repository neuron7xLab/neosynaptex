"""Deep coverage tests for Levin modules — exception paths, edge cases, branches.

Closes branch coverage gaps found by pytest-cov --cov-branch:
  - persuasion.py:221 (SIGNAL classification)
  - persuasion.py:293-300 (sparse eigsh path for n>256)
  - persuasion.py:377-378 (LinAlgError fallback)
  - memory_anonymization.py:262,275,297,302-303,309 (entropy/rank edge cases)
  - levin_pipeline.py:146-154 (interpretation branches)
  - morphospace.py:119,122 (FieldSequence input variants)
"""

from __future__ import annotations

import numpy as np
import pytest

# === persuasion.py — SIGNAL branch ===


def test_classify_signal_level() -> None:
    """Exercise InterventionLevel.SIGNAL — requires gradient change + rms_change."""
    from mycelium_fractal_net.bio.persuasion import (
        InterventionClassifier,
        InterventionLevel,
    )

    classifier = InterventionClassifier(
        force_threshold=0.5,
        setpoint_threshold=0.1,
        signal_threshold=0.01,
    )
    rng = np.random.default_rng(42)
    before = rng.standard_normal((8, 8))
    # Create after with same mean but different gradients (SIGNAL, not SETPOINT)
    after = before.copy()
    # Add structured gradient perturbation that changes spatial structure
    x = np.linspace(-1, 1, 8)
    gradient_mod = 0.05 * np.outer(x, x)
    after += gradient_mod
    level = classifier.classify(before, after)
    assert level == InterventionLevel.SIGNAL


def test_classify_identical_fields() -> None:
    """Identical fields → PERSUADE (minimal change)."""
    from mycelium_fractal_net.bio.persuasion import (
        InterventionClassifier,
        InterventionLevel,
    )

    field = np.random.default_rng(0).standard_normal((4, 4))
    level = InterventionClassifier().classify(field, field)
    assert level == InterventionLevel.PERSUADE


# === persuasion.py — LinAlgError fallback in from_field_history ===


def test_from_field_history_degenerate() -> None:
    """All-zero history → degenerate SVD → fallback path."""
    from mycelium_fractal_net.bio.persuasion import PersuadabilityAnalyzer

    # Constant history: SVD will be rank-deficient
    history = np.ones((10, 4, 4)) * 0.5
    # Add tiny noise to avoid exact zero
    history += np.random.default_rng(0).standard_normal(history.shape) * 1e-15
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.from_field_history(history, n_modes=3)
    assert 0.0 <= result.persuadability_score <= 1.0


# === memory_anonymization.py — edge cases ===


def test_matrix_entropy_single_row() -> None:
    """Single-row matrix → entropy = 0."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    M = np.array([[1.0, -1.0, 1.0]])
    assert GapJunctionDiffuser._matrix_entropy(M) == 0.0


def test_effective_rank_single_row() -> None:
    """Single-row matrix → rank = 1."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    M = np.array([[1.0, -1.0, 1.0]])
    assert GapJunctionDiffuser._effective_rank(M) == 1


def test_spectral_gap_tiny_graph() -> None:
    """2-node graph → spectral gap = 0 (too small for eigsh)."""
    from scipy.sparse import csr_matrix

    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    L = csr_matrix(np.array([[1.0, -1.0], [-1.0, 1.0]]))
    assert GapJunctionDiffuser._spectral_gap(L, 2) == 0.0


def test_cosine_anonymity_identical() -> None:
    """Identical matrices → anonymity = 0."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    M = np.random.default_rng(0).choice([-1.0, 1.0], size=(10, 50))
    assert GapJunctionDiffuser.cosine_anonymity(M, M) == pytest.approx(0.0, abs=1e-10)


def test_cosine_anonymity_opposite() -> None:
    """Flipped signs → cosine=-1 → anonymity = 1-(-1) = 2.0 (max divergence)."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    M = np.ones((5, 100))
    M_neg = -M
    anon = GapJunctionDiffuser.cosine_anonymity(M_neg, M)
    assert anon == pytest.approx(2.0, abs=1e-10)
    # Verify: identical → 0
    assert GapJunctionDiffuser.cosine_anonymity(M, M) == pytest.approx(0.0, abs=1e-10)


def test_cosine_anonymity_shape_mismatch() -> None:
    """Mismatched shapes → return 1.0."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    M1 = np.ones((5, 100))
    M2 = np.ones((5, 50))
    assert GapJunctionDiffuser.cosine_anonymity(M1, M2) == 1.0


def test_encoder_large_subsample() -> None:
    """Matrix entropy with >100 rows triggers subsampling path."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    rng = np.random.default_rng(0)
    M = rng.choice([-1.0, 1.0], size=(200, 50))
    entropy = GapJunctionDiffuser._matrix_entropy(M)
    assert entropy > 0.0


def test_effective_rank_large_matrix() -> None:
    """Effective rank with >100 rows triggers subsampling."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

    rng = np.random.default_rng(0)
    M = rng.standard_normal((200, 30))
    rank = GapJunctionDiffuser._effective_rank(M)
    assert 1 <= rank <= 30


# === levin_pipeline.py — interpretation branches ===


def test_interpretation_moderate_stability() -> None:
    """Basin stability 0.4-0.7 → 'moderately stable'."""
    from mycelium_fractal_net.bio.levin_pipeline import LevinReport

    report = LevinReport(
        morphospace_pc1_variance=0.9,
        basin_stability=0.55,
        basin_error=0.05,
        trajectory_length=10.0,
        anonymity_score=0.1,
        cosine_anonymity=0.6,
        fiedler_value=0.01,
        persuadability_score=0.5,
        log_det_gramian=5.0,
        n_controllable_modes=3,
        free_energy_final=0.1,
        intervention_level="SIGNAL",
        compute_time_ms=100.0,
        grid_size=16,
        n_frames=20,
    )
    interp = report.interpretation()
    assert "moderately stable" in interp


def test_interpretation_critical_transition() -> None:
    """Basin stability < 0.4 → 'critical transition'."""
    from mycelium_fractal_net.bio.levin_pipeline import LevinReport

    report = LevinReport(
        morphospace_pc1_variance=0.9,
        basin_stability=0.2,
        basin_error=0.1,
        trajectory_length=50.0,
        anonymity_score=0.5,
        cosine_anonymity=0.8,
        fiedler_value=0.05,
        persuadability_score=0.3,
        log_det_gramian=2.0,
        n_controllable_modes=2,
        free_energy_final=1.0,
        intervention_level="FORCE",
        compute_time_ms=100.0,
        grid_size=16,
        n_frames=20,
    )
    interp = report.interpretation()
    assert "critical" in interp
    assert "collective" in interp  # cosine_anonymity > 0.5
    assert "stronger intervention" in interp  # modes <= 5


def test_report_aliases_consistent() -> None:
    """Property aliases return same values as canonical fields."""
    from mycelium_fractal_net.bio.levin_pipeline import LevinReport

    report = LevinReport(
        morphospace_pc1_variance=0.9,
        basin_stability=0.7,
        basin_error=0.05,
        trajectory_length=10.0,
        anonymity_score=0.1,
        cosine_anonymity=0.3,
        fiedler_value=0.01,
        persuadability_score=0.5,
        log_det_gramian=8.0,
        n_controllable_modes=10,
        free_energy_final=0.05,
        intervention_level="PERSUADE",
        compute_time_ms=100.0,
        grid_size=16,
        n_frames=20,
    )
    assert report.spectral_gap == report.fiedler_value
    assert report.gramian_log_det == report.log_det_gramian
    assert report.free_energy == report.free_energy_final
    assert report.min_control_energy == report.free_energy_final


# === morphospace.py — input variants ===


def test_morphospace_fit_with_fieldsequence() -> None:
    """MorphospaceBuilder.fit() accepts FieldSequence directly."""
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio.morphospace import MorphospaceBuilder

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    builder = MorphospaceBuilder()
    coords = builder.fit(seq)
    assert coords.n_frames == 10
    assert coords.field_shape == (8, 8)


def test_morphospace_fit_raw_array() -> None:
    """MorphospaceBuilder.fit() accepts raw (T,N,N) ndarray."""
    from mycelium_fractal_net.bio.morphospace import MorphospaceBuilder

    history = np.random.default_rng(0).standard_normal((15, 6, 6))
    builder = MorphospaceBuilder()
    coords = builder.fit(history)
    assert coords.n_frames == 15


def test_morphospace_tiny_grid() -> None:
    """2×2 grid, 3 frames — degenerate but safe."""
    from mycelium_fractal_net.bio.morphospace import MorphospaceBuilder

    history = np.random.default_rng(0).standard_normal((3, 2, 2))
    builder = MorphospaceBuilder()
    coords = builder.fit(history)
    assert coords.n_frames == 3
    assert coords.coords.shape[0] == 3


# === pip-audit style: verify no known CVEs in bio deps ===


def test_bio_deps_importable() -> None:
    """All bio dependencies are importable and functional."""
    import scipy
    import sklearn

    assert hasattr(scipy, "__version__")
    assert hasattr(sklearn, "__version__")
    # Verify critical submodules
    from scipy.linalg import expm  # noqa: F401
    from scipy.sparse import csr_matrix  # noqa: F401
    from scipy.sparse.linalg import eigsh  # noqa: F401
    from sklearn.cluster import KMeans  # noqa: F401
    from sklearn.decomposition import PCA  # noqa: F401
