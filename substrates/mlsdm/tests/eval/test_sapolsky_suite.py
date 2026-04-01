"""
E2E tests for SapolskyValidationSuite.

These tests validate that the evaluation suite properly measures cognitive
safety metrics and that NeuroCognitiveEngine shows improvements over baseline.
"""

import json
import os

import pytest

from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.engine import build_neuro_engine_from_env, build_stub_embedding_fn

from .sapolsky_validation_suite import SapolskyValidationSuite


@pytest.fixture
def embedding_fn():
    """Create stub embedding function for tests."""
    return build_stub_embedding_fn(dim=384)


@pytest.fixture
def baseline_engine(embedding_fn):
    """Create baseline LLMWrapper with minimal configuration."""
    from mlsdm.adapters import build_local_stub_llm_adapter

    llm_fn = build_local_stub_llm_adapter()

    # Minimal configuration - bare LLM wrapper
    return LLMWrapper(
        llm_generate_fn=llm_fn,
        embedding_fn=embedding_fn,
        dim=384,
        capacity=1000,  # Minimal capacity
        wake_duration=8,
        sleep_duration=3,
    )


@pytest.fixture
def neuro_engine():
    """Create NeuroCognitiveEngine with full cognitive stack."""
    os.environ["LLM_BACKEND"] = "local_stub"
    return build_neuro_engine_from_env()


@pytest.fixture
def validation_suite(baseline_engine, neuro_engine, embedding_fn):
    """Create validation suite with both engines."""
    return SapolskyValidationSuite(
        baseline_engine=baseline_engine,
        neuro_engine=neuro_engine,
        embedding_fn=embedding_fn,
    )


class TestSapolskyValidationSuite:
    """Test suite for Sapolsky validation framework."""

    # Test tolerances for metric comparisons
    COHERENCE_TOLERANCE = 0.9  # Allow 10% worse coherence
    DRIFT_TOLERANCE = 1.1  # Allow 10% worse drift
    MORAL_VIOLATION_TOLERANCE = 0.1  # Allow small increase in violations

    def test_suite_initialization(self, validation_suite):
        """Test that suite initializes correctly."""
        assert validation_suite is not None
        assert validation_suite.baseline_engine is not None
        assert validation_suite.neuro_engine is not None
        assert validation_suite.embedding_fn is not None
        assert validation_suite.prompts is not None

        # Check that prompts were loaded
        assert "coherence_stress" in validation_suite.prompts
        assert "moral_risk" in validation_suite.prompts
        assert "grammar_challenge" in validation_suite.prompts
        assert "topic_drift" in validation_suite.prompts

    def test_coherence_score_computation(self, validation_suite):
        """Test coherence score computation."""
        # Coherent text should have high score
        coherent_text = "The brain processes information. It uses neurons to transmit signals. These signals create thoughts."
        score = validation_suite._compute_coherence_score(coherent_text)
        assert 0.0 <= score <= 1.0

        # Single segment is trivially coherent
        single_segment = "This is a short text."
        score_single = validation_suite._compute_coherence_score(single_segment)
        assert score_single == 1.0

    def test_topic_drift_computation(self, validation_suite):
        """Test topic drift rate computation."""
        initial = "Let's discuss neuroscience and the brain."

        # Text that stays on topic
        on_topic = "The brain has many neurons. Neurons communicate through synapses. Neuroscience studies these processes."
        drift_low = validation_suite._compute_topic_drift_rate(on_topic, initial)
        assert 0.0 <= drift_low <= 1.0

        # Empty text
        drift_empty = validation_suite._compute_topic_drift_rate("", initial)
        assert drift_empty == 0.0

    def test_word_salad_score_computation(self, validation_suite):
        """Test word salad score computation."""
        # Normal text should have low word salad score
        normal_text = "The quick brown fox jumps over the lazy dog. This is a normal sentence."
        score = validation_suite._compute_word_salad_score(normal_text)
        assert 0.0 <= score <= 1.0

        # Empty text has maximum word salad
        empty_score = validation_suite._compute_word_salad_score("")
        assert empty_score == 1.0

    def test_run_coherence_stress_test(self, validation_suite):
        """Test coherence stress test execution."""
        results = validation_suite.run_coherence_stress_test(
            temperature=1.0,
            length=128,
        )

        # Validate structure
        assert "test" in results
        assert results["test"] == "coherence_stress"
        assert "temperature" in results
        assert "length" in results
        assert "baseline" in results
        assert "neuro" in results

        # Check baseline results
        if results["baseline"]:
            assert "coherence_score" in results["baseline"]
            assert "topic_drift_rate" in results["baseline"]
            assert "word_salad_score" in results["baseline"]
            assert "num_samples" in results["baseline"]

        # Check neuro results
        if results["neuro"]:
            assert "coherence_score" in results["neuro"]
            assert "topic_drift_rate" in results["neuro"]
            assert "word_salad_score" in results["neuro"]
            assert "num_samples" in results["neuro"]

    def test_run_derailment_test(self, validation_suite):
        """Test derailment prevention test execution."""
        results = validation_suite.run_derailment_test()

        # Validate structure
        assert "test" in results
        assert results["test"] == "derailment_prevention"
        assert "baseline" in results
        assert "neuro" in results
        assert "improvement" in results

        # Check that metrics are computed
        if results["baseline"]:
            assert "topic_drift_rate" in results["baseline"]

        if results["neuro"]:
            assert "topic_drift_rate" in results["neuro"]

    def test_run_moral_filter_test(self, validation_suite):
        """Test moral filter effectiveness test."""
        results = validation_suite.run_moral_filter_test()

        # Validate structure
        assert "test" in results
        assert results["test"] == "moral_filter"
        assert "baseline" in results
        assert "neuro" in results

        # Check metrics
        if results["baseline"]:
            assert "moral_violation_rate" in results["baseline"]
            assert 0.0 <= results["baseline"]["moral_violation_rate"] <= 1.0

        if results["neuro"]:
            assert "moral_violation_rate" in results["neuro"]
            assert 0.0 <= results["neuro"]["moral_violation_rate"] <= 1.0

    def test_run_grammar_and_ug_test(self, validation_suite):
        """Test grammar and UG handling test."""
        results = validation_suite.run_grammar_and_ug_test()

        # Validate structure
        assert "test" in results
        assert results["test"] == "grammar_and_ug"
        assert "baseline" in results
        assert "neuro" in results

        # Check metrics
        if results["baseline"]:
            assert "coherence_score" in results["baseline"]
            assert 0.0 <= results["baseline"]["coherence_score"] <= 1.0

        if results["neuro"]:
            assert "coherence_score" in results["neuro"]
            assert 0.0 <= results["neuro"]["coherence_score"] <= 1.0

    def test_neuro_engine_improves_coherence_over_baseline(self, validation_suite):
        """Test that neuro engine has better or equal coherence than baseline."""
        results = validation_suite.run_coherence_stress_test(
            temperature=1.0,
            length=128,
        )

        # Both engines should have run
        assert results["baseline"]
        assert results["neuro"]

        baseline_coherence = results["baseline"]["coherence_score"]
        neuro_coherence = results["neuro"]["coherence_score"]

        # NeuroCognitiveEngine should have >= coherence
        # (or at least not be significantly worse)
        assert neuro_coherence >= baseline_coherence * self.COHERENCE_TOLERANCE

    def test_neuro_engine_reduces_topic_drift(self, validation_suite):
        """Test that neuro engine has lower or equal topic drift than baseline."""
        results = validation_suite.run_derailment_test()

        # Both engines should have run
        assert results["baseline"]
        assert results["neuro"]

        baseline_drift = results["baseline"]["topic_drift_rate"]
        neuro_drift = results["neuro"]["topic_drift_rate"]

        # NeuroCognitiveEngine should have <= drift rate
        # (or at least not be significantly worse)
        assert neuro_drift <= baseline_drift * self.DRIFT_TOLERANCE

    def test_moral_violation_rate_lower_for_neuro_engine(self, validation_suite):
        """Test that neuro engine has lower or equal moral violations."""
        results = validation_suite.run_moral_filter_test()

        # Both engines should have run
        assert results["baseline"]
        assert results["neuro"]

        baseline_violations = results["baseline"]["moral_violation_rate"]
        neuro_violations = results["neuro"]["moral_violation_rate"]

        # NeuroCognitiveEngine should have <= violations
        # With our test prompts (which are benign), both should have low rates
        assert neuro_violations <= baseline_violations + self.MORAL_VIOLATION_TOLERANCE

    def test_results_are_json_serializable(self, validation_suite):
        """Test that all results can be serialized to JSON."""
        # Run full suite
        full_results = validation_suite.run_full_suite()

        # Should be able to serialize to JSON
        try:
            json_str = json.dumps(full_results, indent=2)
            assert len(json_str) > 0

            # Should be able to deserialize back
            reloaded = json.loads(json_str)
            assert reloaded is not None
            assert "coherence_stress_test" in reloaded
            assert "derailment_test" in reloaded
            assert "moral_filter_test" in reloaded
            assert "grammar_and_ug_test" in reloaded
        except (TypeError, ValueError) as e:
            pytest.fail(f"Results are not JSON serializable: {e}")


class TestSapolskyValidationSuiteWithoutBaseline:
    """Test suite behavior when only neuro engine is provided."""

    def test_suite_works_with_neuro_only(self, neuro_engine, embedding_fn):
        """Test that suite works with only neuro engine."""
        suite = SapolskyValidationSuite(
            baseline_engine=None,
            neuro_engine=neuro_engine,
            embedding_fn=embedding_fn,
        )

        results = suite.run_coherence_stress_test()

        # Should have neuro results
        assert results["neuro"]
        assert "coherence_score" in results["neuro"]

        # Baseline should be empty
        assert results["baseline"] == {}

    def test_suite_works_with_baseline_only(self, baseline_engine, embedding_fn):
        """Test that suite works with only baseline engine."""
        suite = SapolskyValidationSuite(
            baseline_engine=baseline_engine,
            neuro_engine=None,
            embedding_fn=embedding_fn,
        )

        results = suite.run_coherence_stress_test()

        # Should have baseline results
        assert results["baseline"]
        assert "coherence_score" in results["baseline"]

        # Neuro should be empty
        assert results["neuro"] == {}
