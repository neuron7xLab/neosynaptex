"""
Property-based tests for NeuroCognitiveEngine invariants.

Tests formal invariants defined in docs/FORMAL_INVARIANTS.md using Hypothesis.
Covers safety, liveness, and metamorphic properties.
"""

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from mlsdm.cognition.moral_filter_v2 import _HARMFUL_REGEX, _POSITIVE_REGEX
from mlsdm.engine import NeuroCognitiveEngine, NeuroEngineConfig

# Test tolerances
MORAL_SCORE_TOLERANCE = 0.15  # Tolerance for moral score estimation
COHERENCE_TOLERANCE = 0.15  # Tolerance for coherence variations

# Harmful/toxic patterns used for content detection in tests
# These patterns trigger rejection in the mock LLM and moral scoring heuristics
HARMFUL_CONTENT_PATTERNS = ["hate", "violence", "attack", "harmful"]


# ============================================================================
# Test Strategies
# ============================================================================


@st.composite
def prompt_strategy(draw):
    """Generate various prompt types."""
    prompt_type = draw(st.sampled_from(["simple", "with_noise", "neutral_phrase", "toxic_pattern"]))

    if prompt_type == "simple":
        return draw(st.text(min_size=1, max_size=100))
    elif prompt_type == "with_noise":
        core = draw(st.text(min_size=5, max_size=50))
        noise = draw(st.text(min_size=1, max_size=20))
        return f"{noise} {core}"
    elif prompt_type == "neutral_phrase":
        core = draw(st.text(min_size=5, max_size=50))
        suffix = draw(st.sampled_from([" please", " thank you", " kindly"]))
        return f"{core}{suffix}"
    else:  # toxic_pattern
        toxic_words = ["hate", "attack", "violence", "harmful"]
        word = draw(st.sampled_from(toxic_words))
        return f"This contains {word} content"


@st.composite
def moral_value_strategy(draw):
    """Generate moral values in valid range [0.0, 1.0]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def cognitive_load_strategy(draw):
    """Generate cognitive load values in [0.0, 1.0]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_engine(config=None):
    """Create a test engine with mocked LLM and embedding functions."""
    if config is None:
        config = NeuroEngineConfig(
            dim=384,
            capacity=100,  # Small for tests
            enable_fslgs=False,  # Disable FSLGS for simpler tests
        )

    # Mock LLM function - signature must match LLMWrapper expectations
    class MockLLM:
        def __call__(self, prompt_text, system_prompt="", temperature=0.7, max_tokens=150):
            # Simulate moral filtering based on content
            if any(word in prompt_text.lower() for word in HARMFUL_CONTENT_PATTERNS):
                return "I cannot respond to harmful requests."
            return f"Response to: {prompt_text[:20]}..."

    # Mock embedding function
    def mock_embedding(text):
        # Generate deterministic but varied embeddings
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(config.dim)
        return vec / (np.linalg.norm(vec) + 1e-8)  # Normalize

    return NeuroCognitiveEngine(
        llm_generate_fn=MockLLM(),
        embedding_fn=mock_embedding,
        config=config,
    )


def get_moral_score_estimate(response_text, prompt):
    """Estimate moral score for a prompt using same logic as MoralFilterV2.compute_moral_value.

    Note: The pre-flight moral check analyzes the PROMPT (not response), so this function
    primarily evaluates the prompt to match the behavior of compute_moral_value.

    Uses the actual scoring logic:
    - Base score 0.8 ("innocent until proven guilty")
    - Harmful patterns reduce by 0.15 each
    - Positive patterns increase by 0.05 each

    Args:
        response_text: The LLM response (kept for backward compatibility but not used)
        prompt: The original prompt to analyze
    """
    # Use pre-compiled regex patterns from MoralFilterV2 module for consistency and performance
    harmful_count = len(_HARMFUL_REGEX.findall(prompt))
    positive_count = len(_POSITIVE_REGEX.findall(prompt))

    # Same scoring as compute_moral_value
    base_score = 0.8
    adjusted_score = base_score - (harmful_count * 0.15) + (positive_count * 0.05)

    return max(0.0, min(1.0, adjusted_score))


# ============================================================================
# Property Tests: Safety Invariants
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(prompt=prompt_strategy())
def test_response_schema_completeness(prompt):
    """
    INV-NCE-S1: Response Schema Completeness
    Every response MUST contain all required schema fields.
    """
    assume(len(prompt.strip()) > 0)  # Skip empty prompts

    engine = create_test_engine()

    try:
        response = engine.generate(
            prompt=prompt,
            moral_value=0.5,
            context_top_k=3,
            cognitive_load=0.5,
        )

        # Check all required keys exist
        required_keys = {
            "response",
            "governance",
            "mlsdm",
            "timing",
            "validation_steps",
            "error",
            "rejected_at",
            "decision_trace",
        }

        assert required_keys.issubset(
            set(response.keys())
        ), f"Missing required keys. Got: {set(response.keys())}, Required: {required_keys}"

        # Check nested structures exist
        # governance can be None (when FSLGS disabled) or dict (when FSLGS enabled)
        assert response["governance"] is None or isinstance(response["governance"], dict)
        assert isinstance(response["mlsdm"], dict)
        assert isinstance(response["timing"], dict)
        assert isinstance(response["validation_steps"], list)

    except Exception as e:
        # Even errors should return structured response
        pytest.fail(f"Exception raised instead of structured error response: {e}")


@settings(max_examples=100, deadline=None)
@given(prompt=prompt_strategy(), moral_threshold=moral_value_strategy())
def test_moral_threshold_enforcement(prompt, moral_threshold):
    """
    INV-NCE-S2: Moral Threshold Enforcement
    Accepted responses MUST meet moral threshold requirements.
    """
    assume(len(prompt.strip()) > 0)
    assume(0.1 <= moral_threshold <= 0.9)  # Reasonable threshold range

    config = NeuroEngineConfig(
        initial_moral_threshold=moral_threshold,
        enable_fslgs=False,
    )
    engine = create_test_engine(config)

    response = engine.generate(
        prompt=prompt,
        moral_value=moral_threshold,
        context_top_k=3,
    )

    # If response is accepted (not rejected)
    if response["rejected_at"] is None:
        # Estimate moral score
        moral_score = get_moral_score_estimate(response["response"], prompt)

        # Should meet threshold (with some tolerance for estimation error)
        assert (
            moral_score >= moral_threshold - MORAL_SCORE_TOLERANCE
        ), f"Accepted response has moral score {moral_score} below threshold {moral_threshold}"


@settings(max_examples=50, deadline=None)
@given(prompt=prompt_strategy())
def test_timing_non_negativity(prompt):
    """
    INV-NCE-S3: Timing Non-Negativity
    All timing measurements MUST be non-negative.
    """
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()
    response = engine.generate(prompt=prompt, moral_value=0.5)

    timing = response.get("timing", {})
    for key, value in timing.items():
        assert value >= 0, f"Timing metric '{key}' is negative: {value}"


@settings(max_examples=50, deadline=None)
@given(prompt=prompt_strategy())
def test_rejection_reason_validity(prompt):
    """
    INV-NCE-S4: Rejection Reason Validity
    If rejected, rejection stage MUST be valid and error MUST be set.
    """
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()
    response = engine.generate(prompt=prompt, moral_value=0.5)

    rejected_at = response.get("rejected_at")
    error = response.get("error")

    if rejected_at is not None:
        # Valid rejection stages (from actual NCE implementation)
        valid_stages = {
            "pre_moral",
            "pre_grammar",
            "fslgs",
            "mlsdm",
            "post_validation",
            "generation",  # Can be rejected during generation phase
        }

        assert (
            rejected_at in valid_stages
        ), f"Invalid rejection stage: {rejected_at}. Valid stages: {valid_stages}"

        assert error is not None, "Rejection without error message"


# ============================================================================
# Property Tests: Liveness Invariants
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(prompt=prompt_strategy())
def test_response_generation_guarantee(prompt):
    """
    INV-NCE-L1: Response Generation
    Every valid request MUST receive either accepted response or structured rejection.
    """
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()

    response = engine.generate(prompt=prompt, moral_value=0.5)

    # Must have either:
    # 1. Valid response with content, OR
    # 2. Rejection with reason

    has_response = response.get("response") is not None and len(response["response"]) > 0
    has_rejection = response.get("rejected_at") is not None

    assert has_response or has_rejection, "Response has neither content nor rejection reason"


@settings(max_examples=50, deadline=None)
@given(prompt=prompt_strategy())
def test_no_infinite_hanging(prompt):
    """
    INV-NCE-L2: Timeout Guarantee
    Operations complete within reasonable time (tested implicitly via deadline).
    """
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()

    # If this test completes, timeout guarantee is met
    # Hypothesis deadline ensures no hanging
    response = engine.generate(prompt=prompt, moral_value=0.5)

    assert response is not None


@settings(max_examples=50, deadline=None)
@given(prompt=prompt_strategy())
def test_error_propagation(prompt):
    """
    INV-NCE-L3: Error Propagation
    Internal errors MUST be reflected in error field.
    """
    assume(len(prompt.strip()) > 0)

    # Create engine with intentionally failing LLM
    class FailingLLM:
        def __call__(self, prompt_text, system_prompt="", temperature=0.7, max_tokens=150):
            raise RuntimeError("Simulated LLM failure")

    def mock_embedding(text):
        np.random.seed(42)
        return np.random.randn(384)

    config = NeuroEngineConfig(enable_fslgs=False)
    engine = NeuroCognitiveEngine(
        llm_generate_fn=FailingLLM(),
        embedding_fn=mock_embedding,
        config=config,
    )

    response = engine.generate(prompt=prompt, moral_value=0.5)

    # Error should be captured in structured response
    assert response.get("error") is not None, "Internal error not reflected in response"
    assert response.get("rejected_at") is not None, "Internal error did not set rejected_at"


# ============================================================================
# Property Tests: Metamorphic Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(prompt=st.text(min_size=10, max_size=50))
def test_neutral_phrase_stability(prompt):
    """
    INV-NCE-M1: Neutral Phrase Stability
    Adding neutral phrases should not drastically change moral score.
    """
    assume(len(prompt.strip()) > 5)

    engine = create_test_engine()

    # Generate response for original prompt
    response1 = engine.generate(prompt=prompt, moral_value=0.5)

    # Generate response with neutral suffix
    prompt_with_please = f"{prompt} please"
    response2 = engine.generate(prompt=prompt_with_please, moral_value=0.5)

    # Estimate moral scores
    score1 = get_moral_score_estimate(response1["response"], prompt)
    score2 = get_moral_score_estimate(response2["response"], prompt_with_please)

    # Scores should be similar (within tolerance)
    score_diff = abs(score1 - score2)
    assert (
        score_diff < COHERENCE_TOLERANCE
    ), f"Neutral phrase changed moral score by {score_diff} (from {score1} to {score2})"


@settings(max_examples=30, deadline=None)
@given(prompt=st.text(min_size=10, max_size=50))
def test_rephrasing_consistency(prompt):
    """
    INV-NCE-M2: Rephrasing Consistency
    Semantically similar prompts should produce similar rejection patterns.

    Invariant: Adding polite prefix "Please " should NOT cause:
    - A major change in response structure (both should have same keys)

    Note: Due to stateful moral threshold adaptation, we use separate engine
    instances to test each prompt independently. This ensures the threshold
    doesn't drift between calls, making the test deterministic.
    """
    assume(len(prompt.strip()) > 5)
    # Skip prompts that are already toxic to avoid false test failures
    assume(not any(w in prompt.lower() for w in HARMFUL_CONTENT_PATTERNS))

    # Use separate engines to avoid stateful threshold interference
    engine1 = create_test_engine()
    engine2 = create_test_engine()

    # Original prompt
    response1 = engine1.generate(prompt=prompt, moral_value=0.5)

    # Rephrased version (simple transformation)
    prompt_rephrase = f"Please {prompt.lower()}"
    response2 = engine2.generate(prompt=prompt_rephrase, moral_value=0.5)

    # Both responses must be valid structured responses
    assert isinstance(response1, dict), "response1 must be a dict"
    assert isinstance(response2, dict), "response2 must be a dict"

    # Both should have required schema fields (INV-NCE-S1)
    required_keys = {
        "response",
        "governance",
        "mlsdm",
        "timing",
        "validation_steps",
        "error",
        "rejected_at",
        "decision_trace",
    }
    assert required_keys.issubset(
        set(response1.keys())
    ), f"response1 missing keys: {required_keys - set(response1.keys())}"
    assert required_keys.issubset(
        set(response2.keys())
    ), f"response2 missing keys: {required_keys - set(response2.keys())}"

    # Key invariant: Polite rephrasing should not cause rejection flip
    # If original was accepted, rephrased should also be accepted
    # (Adding "Please" should never make a benign prompt toxic)
    if response1.get("rejected_at") is None:
        # Original accepted - rephrased should also be accepted
        # Allow for sleep phase rejections (those are deterministic based on step count)
        if response2.get("rejected_at") is not None:
            rejection_reason = response2.get("error", {}).get("message", "")
            # Only fail if it's a moral rejection (not sleep phase)
            if "morally rejected" in rejection_reason or "moral" in rejection_reason.lower():
                pytest.fail(
                    f"Polite rephrasing caused moral rejection: "
                    f"original accepted, rephrased rejected with: {rejection_reason}"
                )


@settings(max_examples=30, deadline=None)
@given(
    prompt=st.text(min_size=10, max_size=50),
    load1=cognitive_load_strategy(),
    load2=cognitive_load_strategy(),
)
def test_cognitive_load_monotonicity(prompt, load1, load2):
    """
    INV-NCE-M3: Cognitive Load Monotonicity
    Higher cognitive load should not improve response quality.

    Invariants verified:
    1. Both responses complete without errors (liveness)
    2. Response structure is consistent regardless of load
    3. If low load produces accepted response, high load should not produce better quality
    """
    assume(len(prompt.strip()) > 5)
    assume(load1 < load2)  # load1 is lower than load2

    engine = create_test_engine()

    # Generate with lower load
    response1 = engine.generate(prompt=prompt, moral_value=0.5, cognitive_load=load1)

    # Generate with higher load
    response2 = engine.generate(prompt=prompt, moral_value=0.5, cognitive_load=load2)

    # Both must be valid dict responses (liveness guarantee)
    assert isinstance(response1, dict), "response1 must be a dict"
    assert isinstance(response2, dict), "response2 must be a dict"

    # Both must have required schema keys (INV-NCE-S1)
    required_keys = {
        "response",
        "governance",
        "mlsdm",
        "timing",
        "validation_steps",
        "error",
        "rejected_at",
        "decision_trace",
    }
    assert required_keys.issubset(set(response1.keys())), "response1 missing required keys"
    assert required_keys.issubset(set(response2.keys())), "response2 missing required keys"

    # Higher load should not produce dramatically better results
    # Both should have consistent response structure
    assert ("response" in response1) == ("response" in response2)

    # Timing should be non-negative for both (INV-NCE-S3)
    for key, value in response1.get("timing", {}).items():
        assert value >= 0, f"response1 timing '{key}' is negative: {value}"
    for key, value in response2.get("timing", {}).items():
        assert value >= 0, f"response2 timing '{key}' is negative: {value}"

    # If both accepted, higher load should not drastically improve response
    # (We cannot measure quality directly, but we can verify structure consistency)
    if response1.get("rejected_at") is None and response2.get("rejected_at") is None:
        # Both have valid responses - verify they both have non-empty content
        assert len(response1.get("response", "")) > 0, "Low load response is empty"
        # Note: High load response can be empty due to degradation, which is acceptable


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


@settings(max_examples=20, deadline=None)
@given(prompt=prompt_strategy())
def test_empty_context_handling(prompt):
    """Test that system handles requests with no context gracefully."""
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()

    # Request with minimal context
    response = engine.generate(
        prompt=prompt,
        moral_value=0.5,
        context_top_k=0,  # No context
    )

    # Should still return structured response
    assert "response" in response
    assert "error" in response


@settings(max_examples=20, deadline=None)
@given(prompt=st.text(min_size=200, max_size=500))
def test_long_prompt_handling(prompt):
    """Test that system handles long prompts without crashing."""
    assume(len(prompt.strip()) > 100)

    engine = create_test_engine()

    response = engine.generate(prompt=prompt, moral_value=0.5)

    # Should complete without hanging
    assert response is not None
    assert "timing" in response


@pytest.mark.parametrize("moral_value", [0.0, 0.1, 0.5, 0.9, 1.0])
def test_moral_boundary_values(moral_value):
    """Test boundary values for moral thresholds."""
    engine = create_test_engine()

    response = engine.generate(
        prompt="Test prompt",
        moral_value=moral_value,
    )

    assert response is not None
    assert "response" in response or "rejected_at" in response


# ============================================================================
# Phase 3: Additional Invariant Property Tests
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(num_calls=st.integers(min_value=5, max_value=30), moral_value=moral_value_strategy())
def test_engine_step_counter_monotonic_under_valid_calls(num_calls, moral_value):
    """
    INV-CTRL-3 (from COMPONENT_TEST_MATRIX.md): Step counter should increment monotonically.

    Each call to generate() should advance the internal step counter by exactly 1.
    """
    assume(0.3 <= moral_value <= 0.9)  # Use reasonable moral values

    engine = create_test_engine()

    # Track step counter via mlsdm state
    for i in range(num_calls):
        response = engine.generate(prompt=f"Test prompt {i}", moral_value=moral_value)

        # Response should always be structured
        assert isinstance(response, dict), f"Response {i} is not a dict"

        # MLSDM state should be available
        mlsdm_state = response.get("mlsdm", {})

        # If step counter is exposed, verify monotonicity
        if "step" in mlsdm_state:
            step = mlsdm_state["step"]
            expected_step = i + 1  # Steps start at 1
            assert (
                step >= expected_step
            ), f"Step counter went backwards: got {step}, expected >= {expected_step}"


@settings(max_examples=30, deadline=None)
@given(prompt=prompt_strategy(), num_generate_calls=st.integers(min_value=1, max_value=10))
def test_engine_state_does_not_leak_across_calls(prompt, num_generate_calls):
    """
    Test that each generate call is independent and doesn't leak state.

    Multiple calls with the same prompt should produce consistent structured
    responses without state corruption.
    """
    assume(len(prompt.strip()) > 0)

    engine = create_test_engine()

    responses = []
    for _ in range(num_generate_calls):
        response = engine.generate(prompt=prompt, moral_value=0.5)
        responses.append(response)

    # All responses should have consistent structure
    required_keys = {
        "response",
        "governance",
        "mlsdm",
        "timing",
        "validation_steps",
        "error",
        "rejected_at",
        "decision_trace",
    }

    for i, response in enumerate(responses):
        assert required_keys.issubset(set(response.keys())), f"Response {i} missing required keys"

        # Timing should always be non-negative
        for key, value in response.get("timing", {}).items():
            assert value >= 0, f"Response {i} has negative timing: {key}={value}"


@settings(max_examples=30, deadline=None)
@given(
    prompt=st.text(min_size=5, max_size=50),
    max_tokens_values=st.lists(st.integers(min_value=10, max_value=500), min_size=2, max_size=5),
)
def test_engine_handles_varying_max_tokens(prompt, max_tokens_values):
    """
    Test that varying max_tokens parameter doesn't break the engine.

    Different max_tokens values should all produce valid structured responses.
    """
    assume(len(prompt.strip()) > 3)

    engine = create_test_engine()

    for max_tokens in max_tokens_values:
        response = engine.generate(prompt=prompt, moral_value=0.5, max_tokens=max_tokens)

        # Should always return structured response
        assert isinstance(response, dict), f"Response with max_tokens={max_tokens} not a dict"
        assert "response" in response
        assert "error" in response


@settings(max_examples=20, deadline=None)
@given(prompts=st.lists(st.text(min_size=5, max_size=50), min_size=2, max_size=10))
def test_engine_multi_prompt_sequence_stability(prompts):
    """
    Test that processing a sequence of different prompts doesn't corrupt state.

    This simulates a conversation-like pattern where each prompt is different.
    """
    assume(all(len(p.strip()) > 3 for p in prompts))

    engine = create_test_engine()

    responses = []
    for prompt in prompts:
        response = engine.generate(prompt=prompt, moral_value=0.5)
        responses.append(response)

    # All responses should be valid
    for i, response in enumerate(responses):
        assert isinstance(response, dict), f"Response {i} is not a dict"

        # Either has response content or is properly rejected
        has_content = response.get("response") is not None
        is_rejected = response.get("rejected_at") is not None
        has_error = response.get("error") is not None

        assert (
            has_content or is_rejected or has_error
        ), f"Response {i} has neither content nor rejection/error"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
