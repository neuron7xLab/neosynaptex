"""Tests for the 7 cosmic integrations — each first in category."""

import numpy as np
import pytest

from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec


@pytest.fixture
def seq():
    return simulate_history(SimulationSpec(grid_size=32, steps=60, seed=42))


@pytest.fixture
def field(seq):
    return seq.field


@pytest.fixture
def history(seq):
    return seq.history


# ── 1. Entropy Production (Prigogine) ────────────────────────


class TestEntropyProduction:
    def test_sigma_non_negative(self, field):
        from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production
        r = compute_entropy_production(field)
        assert r.sigma >= 0  # 2nd law

    def test_trajectory(self, history):
        from mycelium_fractal_net.analytics.entropy_production import entropy_production_trajectory
        traj = entropy_production_trajectory(history, stride=5)
        assert len(traj) > 0
        assert all(t.sigma >= 0 for t in traj)

    def test_regime_classified(self, field):
        from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production
        r = compute_entropy_production(field)
        assert r.regime in ("equilibrium", "near_equilibrium", "far_from_equilibrium", "dissipative_structure")
        assert r.summary()


# ── 2. Criticality Detector (SOC) ────────────────────────────


class TestCriticalityDetector:
    def test_fingerprint(self, field):
        from mycelium_fractal_net.analytics.criticality_detector import detect_criticality
        fp = detect_criticality(field)
        assert 0 <= fp.criticality_score <= 1
        assert fp.verdict in ("subcritical", "critical", "supercritical", "edge_of_chaos")

    def test_with_history(self, field, history):
        from mycelium_fractal_net.analytics.criticality_detector import detect_criticality
        fp = detect_criticality(field, history=history)
        assert fp.autocorrelation_time >= 0
        assert fp.summary()

    def test_correlation_length(self, field):
        from mycelium_fractal_net.analytics.criticality_detector import detect_criticality
        fp = detect_criticality(field)
        assert fp.correlation_length > 0


# ── 3. Information Geometry (Fisher-Rao) ─────────────────────


class TestInformationGeometry:
    def test_metric(self, field):
        from mycelium_fractal_net.analytics.information_geometry import compute_fisher_rao_metric
        r = compute_fisher_rao_metric(field)
        assert r.metric_trace >= 0
        assert r.n_informative_directions >= 0
        assert r.summary()

    def test_geodesic_self_zero(self, field):
        from mycelium_fractal_net.analytics.information_geometry import geodesic_distance
        d = geodesic_distance(field, field)
        assert d < 1e-6

    def test_geodesic_different(self, field):
        from mycelium_fractal_net.analytics.information_geometry import geodesic_distance
        other = np.random.default_rng(99).random(field.shape)
        d = geodesic_distance(field, other)
        assert d > 0

    def test_transition_indicator(self, field):
        from mycelium_fractal_net.analytics.information_geometry import compute_fisher_rao_metric
        r = compute_fisher_rao_metric(field)
        assert r.phase_transition_indicator >= 0


# ── 4. Pattern Genome ────────────────────────────────────────


class TestPatternGenome:
    def test_encode(self, field):
        from mycelium_fractal_net.analytics.pattern_genome import encode_genome
        g = encode_genome(field)
        assert g.complexity_class in ("trivial", "simple", "moderate", "complex", "hypercritical")
        assert g.topological_entropy >= 0
        assert g.summary()

    def test_fingerprint_length(self, field):
        from mycelium_fractal_net.analytics.pattern_genome import encode_genome
        g = encode_genome(field)
        fp = g.fingerprint()
        assert fp.shape == (64,)
        assert np.all(np.isfinite(fp))

    def test_distance_self_zero(self, field):
        from mycelium_fractal_net.analytics.pattern_genome import encode_genome, genome_distance
        g = encode_genome(field)
        assert genome_distance(g, g) < 1e-10

    def test_distance_different(self, field):
        from mycelium_fractal_net.analytics.pattern_genome import encode_genome, genome_distance
        g1 = encode_genome(field)
        g2 = encode_genome(np.random.default_rng(99).random(field.shape))
        assert genome_distance(g1, g2) > 0


# ── 5. Morphogenetic Field Tensor ────────────────────────────


class TestFieldTensor:
    def test_compute(self, field):
        from mycelium_fractal_net.analytics.morphogenetic_field_tensor import compute_field_tensor
        t = compute_field_tensor(field)
        assert 0 <= t.mean_anisotropy <= 1
        assert 0 <= t.coherence <= 1
        assert t.defect_count >= 0
        assert t.summary()

    def test_uniform_low_anisotropy(self):
        from mycelium_fractal_net.analytics.morphogenetic_field_tensor import compute_field_tensor
        u = np.ones((32, 32)) * 0.5
        t = compute_field_tensor(u)
        assert t.mean_anisotropy < 0.1

    def test_striped_high_anisotropy(self):
        from mycelium_fractal_net.analytics.morphogenetic_field_tensor import compute_field_tensor
        x = np.arange(32)
        u = np.sin(2 * np.pi * x / 8)[None, :] * np.ones((32, 1))
        t = compute_field_tensor(u)
        assert t.mean_anisotropy > 0.5


# ── 6. Attractor Landscape (Waddington) ──────────────────────


class TestAttractorLandscape:
    def test_reconstruct(self, history):
        from mycelium_fractal_net.analytics.attractor_landscape import reconstruct_landscape
        L = reconstruct_landscape(history, n_bins=15)
        assert L.n_attractors >= 1
        assert L.landscape_roughness > 0
        assert L.summary()

    def test_basin_depths_positive(self, history):
        from mycelium_fractal_net.analytics.attractor_landscape import reconstruct_landscape
        L = reconstruct_landscape(history, n_bins=15)
        assert all(d >= 0 for d in L.basin_depths)


# ── 7. Causal Cone ───────────────────────────────────────────


class TestCausalCone:
    def test_compute_cone(self, history):
        from mycelium_fractal_net.analytics.causal_cone import compute_causal_cone
        cone = compute_causal_cone(history, origin_x=16, origin_y=16)
        assert cone.cone_radius_at_T > 0
        assert cone.causal_speed >= 0
        assert cone.influence_map.shape == (history.shape[1], history.shape[2])
        assert cone.summary()

    def test_influence_map(self, history):
        from mycelium_fractal_net.analytics.causal_cone import causal_influence_map
        imap = causal_influence_map(history, n_probes=4)
        assert imap.shape == (history.shape[1], history.shape[2])
        assert imap.max() <= 1.0 + 1e-6
        assert imap.min() >= 0.0

    def test_origin_has_max_influence(self, history):
        from mycelium_fractal_net.analytics.causal_cone import compute_causal_cone
        cone = compute_causal_cone(history, origin_x=16, origin_y=16)
        # Origin should have self-correlation = 1
        assert cone.influence_map[16, 16] >= 0.99
