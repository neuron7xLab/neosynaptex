"""Tests for Choice Operator A_C — symmetry-breaking for computational indeterminacy."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.core.choice_operator import (
    ChoiceResult,
    choice_operator,
    detect_indeterminacy,
    select_by_criticality,
    select_by_perturbation,
)

# ── detect_indeterminacy ─────────────────────────────────────────────


class TestDetectIndeterminacy:
    def test_clear_winner(self) -> None:
        scores = [0.1, 0.5, 0.9]
        report = detect_indeterminacy(scores)
        assert not report.detected
        assert report.n_candidates == 3
        assert report.indeterminate_indices == (0,)

    def test_two_tied(self) -> None:
        scores = [0.30, 0.32, 0.80]
        report = detect_indeterminacy(scores, threshold=0.05)
        assert report.detected
        assert 0 in report.indeterminate_indices
        assert 1 in report.indeterminate_indices
        assert 2 not in report.indeterminate_indices

    def test_all_identical(self) -> None:
        scores = [0.5, 0.5, 0.5, 0.5]
        report = detect_indeterminacy(scores)
        assert report.detected
        assert len(report.indeterminate_indices) == 4
        assert report.score_spread == 0.0

    def test_single_candidate(self) -> None:
        report = detect_indeterminacy([0.42])
        assert not report.detected
        assert report.indeterminate_indices == (0,)

    def test_empty(self) -> None:
        report = detect_indeterminacy([])
        assert not report.detected
        assert report.n_candidates == 0

    def test_threshold_boundary(self) -> None:
        scores = [0.50, 0.55]
        # At threshold=0.05: 0.55 == 0.50 + 0.05 → included
        report = detect_indeterminacy(scores, threshold=0.05)
        assert report.detected

        # At threshold=0.04: 0.55 > 0.50 + 0.04 → not included
        report2 = detect_indeterminacy(scores, threshold=0.04)
        assert not report2.detected

    def test_score_spread_correct(self) -> None:
        scores = [0.40, 0.42, 0.43, 0.90]
        report = detect_indeterminacy(scores, threshold=0.05)
        assert report.detected
        # Spread among tied: 0.43 - 0.40 = 0.03
        assert abs(report.score_spread - 0.03) < 1e-9


# ── select_by_perturbation ───────────────────────────────────────────


class TestSelectByPerturbation:
    @pytest.fixture
    def seq_and_fields(self):
        """Create a FieldSequence and candidate fields with varying structure."""
        from mycelium_fractal_net.types.field import FieldSequence

        rng = np.random.RandomState(42)
        N = 16

        # Source field
        base = rng.uniform(-0.08, 0.01, (N, N))
        seq = FieldSequence(field=base)

        # Candidate 1: smooth (low F response to noise)
        x = np.linspace(0, 2 * np.pi, N)
        X, Y = np.meshgrid(x, x)
        smooth = (np.sin(X) * np.cos(Y) * 0.02 - 0.05).astype(np.float64)

        # Candidate 2: structured spots (medium F response)
        spots = np.full((N, N), -0.07, dtype=np.float64)
        for _ in range(N):
            cx, cy = rng.randint(0, N, 2)
            spots[max(0, cx - 1):cx + 2, max(0, cy - 1):cy + 2] = 0.01

        # Candidate 3: near-critical pattern (high F response)
        critical = rng.choice([-0.08, 0.01], size=(N, N), p=[0.5, 0.5]).astype(np.float64)

        return seq, [smooth, spots, critical]

    def test_returns_valid_index(self, seq_and_fields) -> None:
        seq, fields = seq_and_fields
        idx, deltas = select_by_perturbation(seq, fields)
        assert 0 <= idx < 3
        assert len(deltas) == 3

    def test_deltas_positive(self, seq_and_fields) -> None:
        seq, fields = seq_and_fields
        _, deltas = select_by_perturbation(seq, fields)
        for d in deltas:
            assert d >= 0.0

    def test_deterministic(self, seq_and_fields) -> None:
        seq, fields = seq_and_fields
        idx1, d1 = select_by_perturbation(seq, fields, seed=99)
        idx2, d2 = select_by_perturbation(seq, fields, seed=99)
        assert idx1 == idx2
        assert d1 == d2

    def test_different_seeds_may_differ(self, seq_and_fields) -> None:
        seq, fields = seq_and_fields
        _, d1 = select_by_perturbation(seq, fields, seed=1)
        _, d2 = select_by_perturbation(seq, fields, seed=2)
        # Deltas should differ (different noise realizations)
        assert d1 != d2


# ── select_by_criticality ───────────────────────────────────────────


class TestSelectByCriticality:
    def test_selects_cognitive_center(self) -> None:
        states = [
            {"D_f": 1.5, "R": 0.4},   # edge of window
            {"D_f": 1.75, "R": 0.80},  # center
            {"D_f": 2.0, "R": 0.9},    # other edge
        ]
        idx = select_by_criticality(states)
        assert idx == 1

    def test_prefers_D_f_center(self) -> None:
        states = [
            {"D_f": 1.60, "R": 0.80},  # D_f off center
            {"D_f": 1.74, "R": 0.80},  # D_f very close to center
        ]
        idx = select_by_criticality(states)
        assert idx == 1

    def test_single_candidate(self) -> None:
        assert select_by_criticality([{"D_f": 1.9, "R": 0.5}]) == 0


# ── choice_operator (full pipeline) ─────────────────────────────────


class TestChoiceOperator:
    def test_no_indeterminacy_selects_best(self) -> None:
        result = choice_operator(
            candidates=["A", "B", "C"],
            scores=[0.1, 0.5, 0.9],
        )
        assert result.selected_index == 0
        assert result.method == "score"
        assert not result.indeterminacy.detected

    def test_indeterminacy_with_fields(self) -> None:
        from mycelium_fractal_net.types.field import FieldSequence

        rng = np.random.RandomState(42)
        N = 16
        seq = FieldSequence(field=rng.uniform(-0.08, 0.01, (N, N)))

        fields = [
            rng.uniform(-0.08, 0.01, (N, N)),
            rng.uniform(-0.08, 0.01, (N, N)),
            rng.uniform(-0.08, 0.01, (N, N)),
        ]

        result = choice_operator(
            candidates=["A", "B", "C"],
            scores=[0.50, 0.51, 0.52],
            seq=seq,
            candidate_fields=fields,
            threshold=0.05,
        )
        assert result.indeterminacy.detected
        assert result.method == "perturbation"
        assert result.delta_F is not None
        assert len(result.delta_F) == 3
        assert 0 <= result.selected_index < 3

    def test_indeterminacy_with_ccp(self) -> None:
        ccp_states = [
            {"D_f": 1.60, "R": 0.70},
            {"D_f": 1.76, "R": 0.79},  # closest to center
            {"D_f": 1.90, "R": 0.85},
        ]
        result = choice_operator(
            candidates=["A", "B", "C"],
            scores=[0.50, 0.51, 0.52],
            ccp_states=ccp_states,
            threshold=0.05,
        )
        assert result.indeterminacy.detected
        assert result.method == "criticality"
        assert result.selected_index == 1

    def test_indeterminacy_hash_fallback(self) -> None:
        result = choice_operator(
            candidates=["A", "B"],
            scores=[0.50, 0.50],
            threshold=0.05,
        )
        assert result.indeterminacy.detected
        assert result.method == "hash"
        assert result.selected_index in (0, 1)

    def test_empty_candidates(self) -> None:
        result = choice_operator(candidates=[], scores=[])
        assert result.selected_index == -1
        assert result.method == "score"

    def test_result_has_rationale(self) -> None:
        result = choice_operator(
            candidates=["A", "B", "C"],
            scores=[0.50, 0.51, 0.52],
            ccp_states=[
                {"D_f": 1.7, "R": 0.8},
                {"D_f": 1.75, "R": 0.8},
                {"D_f": 1.8, "R": 0.8},
            ],
            threshold=0.05,
        )
        assert "Indeterminacy detected" in result.rationale
        assert len(result.rationale) > 20

    def test_perturbation_preferred_over_criticality(self) -> None:
        """When both seq+fields and ccp_states are provided, perturbation wins."""
        from mycelium_fractal_net.types.field import FieldSequence

        N = 8
        rng = np.random.RandomState(42)
        seq = FieldSequence(field=rng.uniform(-0.08, 0.01, (N, N)))
        fields = [rng.uniform(-0.08, 0.01, (N, N)) for _ in range(2)]
        ccp = [{"D_f": 1.75, "R": 0.8}, {"D_f": 1.6, "R": 0.7}]

        result = choice_operator(
            candidates=["A", "B"],
            scores=[0.50, 0.50],
            seq=seq,
            candidate_fields=fields,
            ccp_states=ccp,
        )
        assert result.method == "perturbation"

    def test_deterministic_across_calls(self) -> None:
        from mycelium_fractal_net.types.field import FieldSequence

        N = 8
        rng = np.random.RandomState(42)
        seq = FieldSequence(field=rng.uniform(-0.08, 0.01, (N, N)))
        fields = [rng.uniform(-0.08, 0.01, (N, N)) for _ in range(3)]
        scores = [0.50, 0.51, 0.52]

        r1 = choice_operator(candidates=[0, 1, 2], scores=scores,
                             seq=seq, candidate_fields=fields, seed=42)
        # Reset RNG state by using same seed
        rng2 = np.random.RandomState(42)
        seq2 = FieldSequence(field=rng2.uniform(-0.08, 0.01, (N, N)))
        fields2 = [rng2.uniform(-0.08, 0.01, (N, N)) for _ in range(3)]

        r2 = choice_operator(candidates=[0, 1, 2], scores=scores,
                             seq=seq2, candidate_fields=fields2, seed=42)
        assert r1.selected_index == r2.selected_index
        assert r1.delta_F == r2.delta_F


# ── Integration with existing pipeline ───────────────────────────────


class TestChoiceOperatorIntegration:
    def test_works_with_simulated_field(self) -> None:
        """A_C works end-to-end with a real MFN simulation."""
        import mycelium_fractal_net as mfn

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))

        # Generate 3 "candidate" fields by perturbing the source
        rng = np.random.RandomState(42)
        fields = [
            seq.field + rng.normal(0, 0.001, seq.field.shape)
            for _ in range(3)
        ]

        result = choice_operator(
            candidates=["plan_A", "plan_B", "plan_C"],
            scores=[0.40, 0.41, 0.42],
            seq=seq,
            candidate_fields=fields,
            threshold=0.05,
        )
        assert isinstance(result, ChoiceResult)
        assert result.indeterminacy.detected
        assert result.method == "perturbation"
        assert 0 <= result.selected_index < 3

    def test_ccp_gate_validates(self) -> None:
        """Selected candidate is CCP-checked when fields available."""
        import mycelium_fractal_net as mfn

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        fields = [seq.field.copy() for _ in range(2)]

        result = choice_operator(
            candidates=["A", "B"],
            scores=[0.50, 0.50],
            seq=seq,
            candidate_fields=fields,
        )
        # CCP gate should have been checked
        assert result.ccp_valid is not None
