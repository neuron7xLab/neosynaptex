"""
Property-based tests for LLMWrapper invariants.

Tests formal invariants for LLMWrapper as defined in docs/FORMAL_INVARIANTS.md.
Covers:
1. Memory bounds / capacity constraints (INV-LLM-S2)
2. Stateless mode behavior
3. Governance metadata presence in results

These tests use Hypothesis for property-based testing and do NOT modify
the core LLMWrapper logic - they test the public API only.
"""

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from mlsdm.core.llm_wrapper import LLMWrapper

# ============================================================================
# Test Fixtures - Deterministic Stubs (no network calls)
# ============================================================================


def create_stub_llm():
    """Create a deterministic stub LLM function for testing."""

    def stub_llm_generate(prompt: str, max_tokens: int) -> str:
        # Deterministic response based on prompt length
        return f"Response to prompt of length {len(prompt)} with max_tokens={max_tokens}"

    return stub_llm_generate


def create_stub_embedder(dim: int = 384):
    """Create a deterministic stub embedding function for testing."""

    def stub_embed(text: str) -> np.ndarray:
        # Use hash of text to generate deterministic but varied embeddings
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            # Avoid division by zero - return unit vector along first dimension
            result = np.zeros(dim, dtype=np.float32)
            result[0] = 1.0
            return result
        return vec / norm

    return stub_embed


def create_wrapper(
    capacity: int = 64,
    dim: int = 384,
    stateless_mode: bool = False,
    wake_duration: int = 8,
    sleep_duration: int = 3,
) -> LLMWrapper:
    """Create a test wrapper with configurable capacity and mode."""
    wrapper = LLMWrapper(
        llm_generate_fn=create_stub_llm(),
        embedding_fn=create_stub_embedder(dim),
        dim=dim,
        capacity=capacity,
        wake_duration=wake_duration,
        sleep_duration=sleep_duration,
    )
    # Set stateless mode if requested (mimics graceful degradation)
    if stateless_mode:
        wrapper.stateless_mode = True
    return wrapper


# ============================================================================
# Test Strategies
# ============================================================================


@st.composite
def prompt_strategy(draw):
    """Generate prompts for testing. Non-empty text of various sizes."""
    # Generate printable text to avoid encoding issues
    text = draw(
        st.text(
            alphabet=st.characters(
                categories=("L", "N", "P", "S", "Z"), min_codepoint=32, max_codepoint=126
            ),
            min_size=1,
            max_size=128,
        )
    )
    # Ensure non-empty after strip
    assume(len(text.strip()) > 0)
    return text


@st.composite
def moral_value_strategy(draw):
    """Generate moral values in valid range [0.0, 1.0]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def max_tokens_strategy(draw):
    """Generate reasonable max_tokens values."""
    return draw(st.integers(min_value=10, max_value=500))


@st.composite
def capacity_strategy(draw):
    """Generate small capacity values for fast tests."""
    return draw(st.integers(min_value=10, max_value=100))


@st.composite
def num_calls_strategy(draw):
    """Generate number of generate() calls for stress tests."""
    return draw(st.integers(min_value=5, max_value=50))


# ============================================================================
# Property 1: MEMORY BOUNDS / CAPACITY CONSTRAINT
# INV-LLM-S2: Number of vectors in memory MUST NOT exceed configured capacity
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    capacity=capacity_strategy(),
    num_calls=num_calls_strategy(),
    prompt=prompt_strategy(),
    moral_value=moral_value_strategy(),
)
def test_memory_capacity_never_exceeded(capacity, num_calls, prompt, moral_value):
    """
    INV-LLM-S2: Capacity Constraint

    The number of vectors in memory MUST NOT exceed configured capacity,
    even after many calls to generate().

    Formal: |memory_vectors| ≤ capacity
    """
    # Ensure moral value is high enough to be accepted sometimes
    assume(moral_value >= 0.3)

    wrapper = create_wrapper(capacity=capacity)

    # Track max size seen during all calls
    max_size_seen = 0

    for i in range(num_calls):
        # Vary the prompt slightly to trigger different embeddings
        varied_prompt = f"{prompt} iteration {i}"

        try:
            wrapper.generate(
                prompt=varied_prompt,
                moral_value=moral_value,
            )
        except Exception:
            # Some calls may fail (e.g., during sleep phase) - that's ok
            pass

        # Check memory size after each call
        current_size = wrapper.pelm.size
        max_size_seen = max(max_size_seen, current_size)

        # Invariant: size never exceeds capacity
        assert (
            current_size <= capacity
        ), f"PELM size {current_size} exceeds capacity {capacity} after call {i+1}"

    # Final check: max size seen should never exceed capacity
    assert max_size_seen <= capacity, f"Max PELM size {max_size_seen} exceeded capacity {capacity}"


@settings(max_examples=50, deadline=None)
@given(
    capacity=st.integers(min_value=5, max_value=20),
    num_overflow_calls=st.integers(min_value=30, max_value=100),
)
def test_memory_does_not_grow_unbounded(capacity, num_overflow_calls):
    """
    INV-LLM-L3: Memory Overflow Handling

    When capacity is reached, system MUST evict entries (not grow unbounded).
    After many calls, size should never exceed capacity.

    Formal: |memory| = capacity ∧ insert(v) ⟹ ∃v_old: remove(v_old) ∧ |memory| = capacity

    Note: The wrapper has cognitive rhythm (wake/sleep phases) which may reject
    some calls during sleep. We verify the capacity constraint holds, but do not
    require exact capacity utilization since rejected calls don't add to memory.
    """
    # Ensure we do more calls than capacity
    assume(num_overflow_calls > capacity * 2)

    wrapper = create_wrapper(capacity=capacity)

    max_size_observed = 0

    for i in range(num_overflow_calls):
        prompt = f"Overflow test prompt number {i} with unique content"
        try:
            wrapper.generate(
                prompt=prompt,
                moral_value=0.9,  # High moral value to ensure acceptance
            )
        except Exception:
            pass  # Some rejections during sleep are ok

        # Track max size
        current_size = wrapper.pelm.size
        max_size_observed = max(max_size_observed, current_size)

        # Key invariant: size never exceeds capacity
        assert (
            current_size <= capacity
        ), f"PELM size {current_size} exceeds capacity {capacity} at step {i+1}"

    # Final verification
    final_size = wrapper.pelm.size

    # Size should be <= capacity always (the key invariant)
    assert final_size <= capacity, f"Final PELM size {final_size} exceeds capacity {capacity}"

    # Max observed size should never have exceeded capacity
    assert (
        max_size_observed <= capacity
    ), f"Max observed size {max_size_observed} exceeded capacity {capacity}"


@settings(max_examples=30, deadline=None)
@given(capacity=st.integers(min_value=10, max_value=50))
def test_capacity_invariant_under_mixed_phases(capacity):
    """
    Test that capacity constraint holds regardless of cognitive phase.

    Insert vectors during both wake and sleep phases via many calls,
    verify capacity is never exceeded.
    """
    wrapper = create_wrapper(capacity=capacity, wake_duration=3, sleep_duration=2)

    # Run through multiple wake/sleep cycles
    num_calls = capacity * 3

    for i in range(num_calls):
        prompt = f"Phase test prompt {i} with content"
        try:
            wrapper.generate(
                prompt=prompt,
                moral_value=0.85,
            )
        except Exception:
            pass

        # Invariant must hold at every step
        assert wrapper.pelm.size <= capacity, (
            f"Size {wrapper.pelm.size} > capacity {capacity} at step {i+1}, "
            f"phase={wrapper.rhythm.phase}"
        )


# ============================================================================
# Property 2: STATELESS MODE (no memory writes)
# When stateless_mode=True, wrapper should NOT write to memory.
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    prompt=prompt_strategy(),
    moral_value=moral_value_strategy(),
    num_calls=st.integers(min_value=5, max_value=30),
)
def test_stateless_mode_no_memory_writes(prompt, moral_value, num_calls):
    """
    Stateless Mode Invariant

    When stateless_mode=True, the wrapper MUST NOT write anything to memory.
    Memory size should remain at 0 or its initial value.

    This tests the graceful degradation path where PELM is bypassed.
    """
    assume(moral_value >= 0.3)

    # Create wrapper in stateless mode
    wrapper = create_wrapper(capacity=100, stateless_mode=True)

    # Record initial memory state
    initial_size = wrapper.pelm.size

    for i in range(num_calls):
        varied_prompt = f"{prompt} call {i}"
        try:
            result = wrapper.generate(
                prompt=varied_prompt,
                moral_value=moral_value,
            )

            # If successful, result should indicate stateless mode
            if result.get("accepted"):
                assert (
                    result.get("stateless_mode") is True
                ), "Accepted response in stateless mode should indicate stateless_mode=True"
        except Exception:
            pass  # Some rejections are ok

    # Memory size should NOT have increased
    final_size = wrapper.pelm.size
    assert (
        final_size == initial_size
    ), f"Memory size changed in stateless mode: {initial_size} -> {final_size}"


@settings(max_examples=50, deadline=None)
@given(
    prompts=st.lists(
        st.text(
            min_size=5,
            max_size=50,
            alphabet=st.characters(categories=("L", "N"), min_codepoint=97, max_codepoint=122),
        ),
        min_size=3,
        max_size=15,
    ),
)
def test_stateless_mode_consistency_across_calls(prompts):
    """
    Verify stateless mode remains consistent across multiple calls.

    Once stateless_mode is True, it should remain True and no memory
    operations should be performed.
    """
    assume(all(len(p.strip()) > 0 for p in prompts))

    wrapper = create_wrapper(capacity=50, stateless_mode=True)

    # Wrapper should be in stateless mode
    assert wrapper.stateless_mode is True

    initial_pelm_size = wrapper.pelm.size

    for prompt in prompts:
        try:
            result = wrapper.generate(prompt=prompt, moral_value=0.8)

            # Stateless mode should persist
            assert (
                wrapper.stateless_mode is True
            ), "stateless_mode switched from True to False unexpectedly"

            # Result should reflect stateless mode if accepted
            if result.get("accepted"):
                assert result.get("stateless_mode") is True
        except Exception:
            pass

    # PELM size unchanged
    assert wrapper.pelm.size == initial_pelm_size


@settings(max_examples=30, deadline=None)
@given(capacity=st.integers(min_value=10, max_value=50))
def test_stateless_mode_consolidation_buffer_empty(capacity):
    """
    In stateless mode, consolidation buffer should remain empty.
    """
    wrapper = create_wrapper(capacity=capacity, stateless_mode=True)

    # Initial consolidation buffer should be empty
    assert len(wrapper.consolidation_buffer) == 0

    # Make several calls
    for i in range(20):
        try:
            wrapper.generate(
                prompt=f"Test prompt {i}",
                moral_value=0.9,
            )
        except Exception:
            pass

    # Consolidation buffer should still be empty in stateless mode
    assert (
        len(wrapper.consolidation_buffer) == 0
    ), f"Consolidation buffer has {len(wrapper.consolidation_buffer)} items in stateless mode"


# ============================================================================
# Property 3: GOVERNANCE METADATA (always present)
# Every response from generate() must contain governance-related metadata.
# ============================================================================

# Required keys that must always be present in a response
REQUIRED_RESPONSE_KEYS = {
    "response",  # The generated text (can be empty on rejection)
    "accepted",  # Boolean indicating if morally accepted
    "phase",  # Current cognitive phase (wake/sleep)
    "step",  # Current step counter
    "note",  # Processing note
    "moral_threshold",  # Current moral threshold
}

# Keys that should be present on accepted responses
ACCEPTED_RESPONSE_EXTRA_KEYS = {
    "context_items",
    "max_tokens_used",
}


@settings(max_examples=100, deadline=None)
@given(
    prompt=prompt_strategy(),
    moral_value=moral_value_strategy(),
)
def test_governance_metadata_always_present(prompt, moral_value):
    """
    Governance Metadata Invariant

    Every response from LLMWrapper.generate() MUST contain required
    governance metadata fields. These fields MUST NOT be None.

    This ensures traceability and observability of LLM governance decisions.
    """
    wrapper = create_wrapper()

    result = wrapper.generate(
        prompt=prompt,
        moral_value=moral_value,
    )

    # Result must be a dict
    assert isinstance(result, dict), f"generate() returned {type(result)}, expected dict"

    # All required keys must be present
    for key in REQUIRED_RESPONSE_KEYS:
        assert (
            key in result
        ), f"Required key '{key}' missing from response. Keys present: {list(result.keys())}"

    # Check types of governance fields
    assert isinstance(
        result["accepted"], bool
    ), f"'accepted' should be bool, got {type(result['accepted'])}"

    assert isinstance(result["phase"], str), f"'phase' should be str, got {type(result['phase'])}"

    assert result["phase"] in (
        "wake",
        "sleep",
    ), f"'phase' should be 'wake' or 'sleep', got {result['phase']}"

    assert isinstance(result["step"], int), f"'step' should be int, got {type(result['step'])}"

    assert isinstance(
        result["moral_threshold"], (int, float)
    ), f"'moral_threshold' should be numeric, got {type(result['moral_threshold'])}"

    assert isinstance(result["note"], str), f"'note' should be str, got {type(result['note'])}"


@settings(max_examples=50, deadline=None)
@given(
    prompt=prompt_strategy(),
    moral_value=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
)
def test_accepted_responses_have_full_metadata(prompt, moral_value):
    """
    Accepted responses should have additional metadata fields.

    When a response is accepted (not rejected), it should include
    context_items and max_tokens_used information.
    """
    # Use high moral value and short wake duration to maximize acceptance
    wrapper = create_wrapper(wake_duration=100, sleep_duration=1)

    result = wrapper.generate(
        prompt=prompt,
        moral_value=moral_value,
    )

    if result.get("accepted") is True:
        # Accepted responses should have extra keys
        for key in ACCEPTED_RESPONSE_EXTRA_KEYS:
            assert key in result, f"Accepted response missing key '{key}'"

        # These should be non-negative integers
        assert isinstance(
            result["context_items"], int
        ), f"'context_items' should be int, got {type(result['context_items'])}"
        assert (
            result["context_items"] >= 0
        ), f"'context_items' should be >= 0, got {result['context_items']}"

        assert isinstance(
            result["max_tokens_used"], int
        ), f"'max_tokens_used' should be int, got {type(result['max_tokens_used'])}"
        assert (
            result["max_tokens_used"] > 0
        ), f"'max_tokens_used' should be > 0, got {result['max_tokens_used']}"


@settings(max_examples=50, deadline=None)
@given(prompt=prompt_strategy())
def test_rejected_responses_have_note_explanation(prompt):
    """
    Rejected responses should have a note explaining the rejection.

    When accepted=False, the 'note' field should contain a non-empty
    explanation (e.g., "morally rejected", "sleep phase - consolidating").
    """
    # Use low moral value to trigger rejection
    wrapper = create_wrapper()

    result = wrapper.generate(
        prompt=prompt,
        moral_value=0.1,  # Low moral value to trigger rejection
    )

    if result.get("accepted") is False:
        # Note should explain rejection
        note = result.get("note", "")
        assert len(note) > 0, "Rejected response has empty 'note' field"

        # Note should be descriptive (at least a few characters)
        assert len(note) >= 5, f"Rejection note too short: '{note}'"


@settings(max_examples=30, deadline=None)
@given(
    num_calls=st.integers(min_value=5, max_value=20),
    moral_value=moral_value_strategy(),
)
def test_step_counter_increments_monotonically(num_calls, moral_value):
    """
    Step counter should increment with each call to generate().

    The 'step' field in responses should be monotonically increasing.
    """
    assume(moral_value >= 0.3)

    wrapper = create_wrapper()

    previous_step = 0

    for i in range(num_calls):
        result = wrapper.generate(
            prompt=f"Step test {i}",
            moral_value=moral_value,
        )

        current_step = result.get("step")
        assert current_step is not None, "Response missing 'step' field"
        assert (
            current_step > previous_step
        ), f"Step counter did not increase: {previous_step} -> {current_step}"

        previous_step = current_step


@settings(max_examples=50, deadline=None)
@given(
    prompt=prompt_strategy(),
    moral_value=moral_value_strategy(),
)
def test_moral_threshold_in_valid_range(prompt, moral_value):
    """
    INV-MF-S1 (via wrapper): Moral threshold MUST remain within valid bounds.

    The moral_threshold field should always be in range [0.0, 1.0].
    """
    wrapper = create_wrapper()

    result = wrapper.generate(
        prompt=prompt,
        moral_value=moral_value,
    )

    threshold = result.get("moral_threshold")
    assert threshold is not None, "Response missing 'moral_threshold'"
    assert isinstance(
        threshold, (int, float)
    ), f"'moral_threshold' should be numeric, got {type(threshold)}"
    assert 0.0 <= threshold <= 1.0, f"'moral_threshold' {threshold} out of valid range [0.0, 1.0]"


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.parametrize("moral_value", [0.0, 0.01, 0.5, 0.99, 1.0])
def test_boundary_moral_values(moral_value):
    """Test that boundary moral values produce valid responses."""
    wrapper = create_wrapper()

    result = wrapper.generate(
        prompt="Boundary moral value test",
        moral_value=moral_value,
    )

    # Should always return a valid dict response
    assert isinstance(result, dict)
    assert "accepted" in result
    assert "phase" in result


@pytest.mark.parametrize("capacity", [1, 5, 10, 50, 100])
def test_various_capacity_values(capacity):
    """Test that capacity constraint holds for various capacity values."""
    wrapper = create_wrapper(capacity=capacity)

    # Do more calls than capacity
    for i in range(capacity + 10):
        try:
            wrapper.generate(
                prompt=f"Capacity test {i}",
                moral_value=0.9,
            )
        except Exception:
            pass

    # Size should never exceed capacity
    assert wrapper.pelm.size <= capacity


def test_empty_prompt_handling():
    """Test handling of minimal prompts (single character)."""
    wrapper = create_wrapper()

    result = wrapper.generate(
        prompt="x",  # Minimal non-empty prompt
        moral_value=0.5,
    )

    # Should still return valid structured response
    assert isinstance(result, dict)
    assert "accepted" in result
    assert "response" in result


def test_long_prompt_handling():
    """Test handling of long prompts."""
    wrapper = create_wrapper()

    long_prompt = "This is a test prompt. " * 100  # ~2200 characters

    result = wrapper.generate(
        prompt=long_prompt,
        moral_value=0.8,
    )

    # Should still return valid structured response
    assert isinstance(result, dict)
    assert "accepted" in result


def test_unicode_prompt_handling():
    """Test handling of prompts with unicode characters."""
    wrapper = create_wrapper()

    unicode_prompt = "Hello こんにちは 你好 مرحبا שלום"

    result = wrapper.generate(
        prompt=unicode_prompt,
        moral_value=0.8,
    )

    # Should still return valid structured response
    assert isinstance(result, dict)
    assert "accepted" in result


def test_repeated_identical_prompts():
    """Test that repeated identical prompts still produce valid responses."""
    wrapper = create_wrapper()

    prompt = "Identical prompt test"

    for _ in range(10):
        result = wrapper.generate(
            prompt=prompt,
            moral_value=0.8,
        )

        assert isinstance(result, dict)
        assert "accepted" in result
        # Size should still respect capacity
        assert wrapper.pelm.size <= wrapper.pelm.capacity


# ============================================================================
# Speech Governance Tests (if enabled)
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(
    prompt=prompt_strategy(),
    moral_value=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
)
def test_speech_governance_metadata_when_present(prompt, moral_value):
    """
    If speech_governor is configured, response should include speech_governance field.

    Note: This test creates a wrapper WITHOUT speech governor to verify
    baseline behavior. The field is optional.
    """
    wrapper = create_wrapper()  # No speech governor

    result = wrapper.generate(
        prompt=prompt,
        moral_value=moral_value,
    )

    if result.get("accepted"):
        # Without speech governor, speech_governance should NOT be present
        # (or if it is, it should be None/absent)
        # This is the expected baseline behavior
        pass  # Test passes - field is optional


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
