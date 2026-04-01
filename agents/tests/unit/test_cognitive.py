"""Tests for cognitive strategies and engine."""

from __future__ import annotations

from neuron7x_agents.cognitive.engine import CognitiveEngine, Domain
from neuron7x_agents.cognitive.strategies import (
    AbductiveInference,
    EpistemicForaging,
    ForagingQuestion,
    Hypothesis,
    PredictiveCoding,
    ReductioAdAbsurdum,
)
from neuron7x_agents.primitives.column import Complexity


class TestPredictiveCoding:
    def test_perfect_prediction(self) -> None:
        pc = PredictiveCoding()
        pred = pc.predict({"expected_outcome": "rain"}, prior=0.8)
        error = pc.observe(pred, "rain")
        assert error.error_magnitude == 0.0
        assert error.triggers_abduction is False

    def test_wrong_prediction_triggers_abduction(self) -> None:
        pc = PredictiveCoding(abduction_threshold=0.3)
        pred = pc.predict({"expected_outcome": "rain"}, prior=0.4)
        error = pc.observe(pred, "sunshine")
        assert error.error_magnitude > 0
        assert error.triggers_abduction is True

    def test_cumulative_surprise(self) -> None:
        pc = PredictiveCoding()
        pred = pc.predict({"expected_outcome": "A"}, prior=0.5)
        pc.observe(pred, "B")
        assert pc.cumulative_surprise > 0

    def test_empty_surprise(self) -> None:
        pc = PredictiveCoding()
        assert pc.cumulative_surprise == 0.0


class TestAbductiveInference:
    def test_rank_by_score(self) -> None:
        ab = AbductiveInference()
        h1 = Hypothesis("A", parsimony=0.9, falsifiability=0.8)
        h2 = Hypothesis("B", parsimony=0.5, falsifiability=0.5)
        ranked = ab.rank([h2, h1])
        assert ranked[0].description == "A"

    def test_needs_foraging_when_close(self) -> None:
        ab = AbductiveInference(foraging_margin=0.2)
        h1 = Hypothesis("A", parsimony=0.7, falsifiability=0.7)
        h2 = Hypothesis("B", parsimony=0.7, falsifiability=0.65)
        assert ab.needs_foraging([h1, h2]) is True

    def test_best_returns_none_when_insufficient(self) -> None:
        ab = AbductiveInference(min_hypotheses=2)
        h1 = Hypothesis("A", parsimony=0.9, falsifiability=0.9)
        assert ab.best([h1]) is None

    def test_best_returns_winner(self) -> None:
        ab = AbductiveInference()
        h1 = Hypothesis("A", parsimony=0.9, falsifiability=0.9)
        h2 = Hypothesis("B", parsimony=0.3, falsifiability=0.3)
        result = ab.best([h1, h2])
        assert result is not None
        assert result.description == "A"

    def test_contradicting_evidence_reduces_score(self) -> None:
        h = Hypothesis("A", parsimony=0.9, falsifiability=0.9, contradicting_evidence=["x", "y"])
        assert h.score < 0.81  # base 0.81 - 0.2 penalty


class TestReductio:
    def test_survives_with_contradiction(self) -> None:
        r = ReductioAdAbsurdum()
        result = r.test(
            claim="gamma oscillations synchronize cognition",
            negation="gamma oscillations do not synchronize cognition",
            established_facts=["gamma oscillations measured during cognition tasks"],
        )
        assert result.survived is True

    def test_fails_without_contradiction(self) -> None:
        r = ReductioAdAbsurdum()
        result = r.test(
            claim="X causes Y",
            negation="X does not cause Y",
            established_facts=["unrelated fact about Z"],
        )
        assert result.survived is False


class TestEpistemicForaging:
    def test_highest_impact(self) -> None:
        ef = EpistemicForaging()
        ef.add_question(ForagingQuestion("Q1", expected_impact=0.3))
        ef.add_question(ForagingQuestion("Q2", expected_impact=0.9))
        ef.add_question(ForagingQuestion("Q3", expected_impact=0.1))
        top = ef.highest_impact(2)
        assert top[0].question == "Q2"
        assert len(top) == 2

    def test_needs_more_evidence(self) -> None:
        ef = EpistemicForaging(impact_threshold=0.5)
        ef.add_question(ForagingQuestion("Q1", expected_impact=0.8))
        assert ef.needs_more_evidence() is True


class TestCognitiveEngine:
    def test_reason_returns_result(self) -> None:
        engine = CognitiveEngine(domain=Domain.ANALYSIS)
        result = engine.reason("What is gamma?")
        assert result.domain == Domain.ANALYSIS
        assert result.confidence.calibrated_score >= 0.0

    def test_complexity_affects_column(self) -> None:
        engine = CognitiveEngine()
        r1 = engine.reason("X", complexity=Complexity.TRIVIAL)
        r2 = engine.reason("X", complexity=Complexity.CRITICAL)
        assert len(r1.column_result.role_results) < len(r2.column_result.role_results)
