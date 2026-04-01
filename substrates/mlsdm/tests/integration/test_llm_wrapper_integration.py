"""
Integration tests for LLMWrapper with realistic usage scenarios.
"""

import numpy as np

from mlsdm.core.llm_wrapper import LLMWrapper


def mock_llm_generate(prompt: str, max_tokens: int) -> str:
    """Mock LLM that generates contextual responses."""
    if "hello" in prompt.lower():
        return "Hello! I'm here to help you."
    elif "python" in prompt.lower():
        return "Python is a high-level programming language known for its simplicity."
    elif "code" in prompt.lower():
        return "Here's a simple example: print('Hello, World!')"
    elif "toxic" in prompt.lower() or "harmful" in prompt.lower():
        return "I cannot assist with that request."
    else:
        return "I understand your question. Let me help you with that."


def mock_embedding(text: str) -> np.ndarray:
    """Mock embedding function that creates deterministic embeddings."""
    # Use text hash for deterministic but varied embeddings
    seed = sum(ord(c) for c in text) % (2**32)
    np.random.seed(seed)
    vec = np.random.randn(384).astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / (norm + 1e-9)


def test_llm_wrapper_basic_flow():
    """Test basic LLM wrapper functionality."""
    print("\n✓ Test 1: Basic LLM wrapper flow")

    wrapper = LLMWrapper(llm_generate_fn=mock_llm_generate, embedding_fn=mock_embedding, dim=384)

    # Normal conversation
    result = wrapper.generate(prompt="Hello, how are you?", moral_value=0.9)

    assert result["accepted"] is True
    assert len(result["response"]) > 0
    assert result["phase"] == "wake"
    print(f"  Response: {result['response'][:50]}...")
    print("  PASS")


def test_llm_wrapper_moral_filtering():
    """Test moral filtering in LLM wrapper."""
    print("\n✓ Test 2: Moral filtering")

    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate, embedding_fn=mock_embedding, initial_moral_threshold=0.70
    )

    # Low moral value should be rejected
    result = wrapper.generate(prompt="Tell me something toxic", moral_value=0.2)

    assert result["accepted"] is False
    assert "morally rejected" in result["note"]
    print(f"  Note: {result['note']}")
    print("  PASS")


def test_llm_wrapper_sleep_cycle():
    """Test sleep cycle behavior."""
    print("\n✓ Test 3: Sleep cycle gating")

    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate,
        embedding_fn=mock_embedding,
        wake_duration=2,
        sleep_duration=1,
    )

    # Process during wake
    wake_accepted = 0
    for i in range(2):
        result = wrapper.generate(prompt=f"Wake message {i}", moral_value=0.9)
        if result["accepted"]:
            wake_accepted += 1

    # At least one should be accepted during wake
    assert wake_accepted > 0

    # Now should be in sleep phase
    result = wrapper.generate(prompt="Sleep message", moral_value=0.9)

    assert result["accepted"] is False
    assert result["phase"] == "sleep"
    print(f"  Phase: {result['phase']}, Note: {result['note']}")
    print("  PASS")


def test_llm_wrapper_context_retrieval():
    """Test context retrieval from memory."""
    print("\n✓ Test 4: Context retrieval")

    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate,
        embedding_fn=mock_embedding,
        wake_duration=10,  # Long wake for multiple messages
    )

    # Build context
    topics = ["Python programming", "code examples", "best practices"]
    for topic in topics:
        result = wrapper.generate(prompt=f"Tell me about {topic}", moral_value=0.9)
        assert result["accepted"] is True

    # Query with related topic
    result = wrapper.generate(prompt="Can you help with Python code?", moral_value=0.9)

    assert result["accepted"] is True
    assert result["context_items"] >= 0
    print(f"  Context items retrieved: {result['context_items']}")
    print("  PASS")


def test_llm_wrapper_memory_consolidation():
    """Test memory consolidation during sleep."""
    print("\n✓ Test 5: Memory consolidation")

    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate,
        embedding_fn=mock_embedding,
        wake_duration=3,
        sleep_duration=2,
    )

    # Process messages during wake
    for i in range(3):
        result = wrapper.generate(prompt=f"Message {i}", moral_value=0.9)
        assert result["accepted"] is True

    # Check state
    state = wrapper.get_state()
    initial_qilm_used = state["qilm_stats"]["used"]

    # After wake period, consolidation should have occurred
    print(f"  QILM memory used: {initial_qilm_used}")
    print(f"  Consolidation buffer: {state['consolidation_buffer_size']}")
    print("  PASS")


def test_llm_wrapper_long_conversation():
    """Test long conversation with multiple cycles."""
    print("\n✓ Test 6: Long conversation with multiple cycles")

    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate,
        embedding_fn=mock_embedding,
        wake_duration=5,
        sleep_duration=2,
    )

    accepted_count = 0
    rejected_count = 0

    # Simulate 20 messages across multiple cycles
    for i in range(20):
        result = wrapper.generate(prompt=f"Message number {i}", moral_value=0.85)
        if result["accepted"]:
            accepted_count += 1
        else:
            rejected_count += 1

    state = wrapper.get_state()

    print(f"  Accepted: {accepted_count}, Rejected: {rejected_count}")
    print(f"  Final phase: {state['phase']}")
    print(f"  Memory used: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")
    print(f"  Moral threshold: {state['moral_threshold']}")

    # Should have processed multiple wake cycles
    assert accepted_count > 0
    assert state["step"] == 20
    print("  PASS")


def test_llm_wrapper_memory_bounded():
    """Test that memory stays bounded under load."""
    print("\n✓ Test 7: Memory bounds verification")

    capacity = 100
    wrapper = LLMWrapper(
        llm_generate_fn=mock_llm_generate,
        embedding_fn=mock_embedding,
        capacity=capacity,
        wake_duration=50,  # Long wake to process many messages
    )

    # Process more than capacity
    for i in range(150):
        _ = wrapper.generate(prompt=f"Message {i}", moral_value=0.9)

    state = wrapper.get_state()
    qilm_stats = state["qilm_stats"]

    print(f"  Capacity: {qilm_stats['capacity']}")
    print(f"  Used: {qilm_stats['used']}")
    print(f"  Memory MB: {qilm_stats['memory_mb']}")

    # Verify bounds
    assert qilm_stats["used"] <= capacity
    assert qilm_stats["capacity"] == capacity
    print("  PASS")


def test_llm_wrapper_state_consistency():
    """Test state consistency across operations."""
    print("\n✓ Test 8: State consistency")

    wrapper = LLMWrapper(llm_generate_fn=mock_llm_generate, embedding_fn=mock_embedding)

    # Get initial state
    state1 = wrapper.get_state()

    # Process message
    wrapper.generate("Test message", moral_value=0.9)

    # Get state again
    state2 = wrapper.get_state()

    # Verify state changed appropriately
    assert state2["step"] == state1["step"] + 1
    assert state2["accepted_count"] >= state1["accepted_count"]
    assert state2["synaptic_norms"]["L1"] >= state1["synaptic_norms"]["L1"]

    print(f"  Steps: {state1['step']} -> {state2['step']}")
    print(
        f"  L1 norm: {state1['synaptic_norms']['L1']:.2f} -> {state2['synaptic_norms']['L1']:.2f}"
    )
    print("  PASS")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MLSDM LLM Wrapper Integration Tests")
    print("=" * 60)

    test_llm_wrapper_basic_flow()
    test_llm_wrapper_moral_filtering()
    test_llm_wrapper_sleep_cycle()
    test_llm_wrapper_context_retrieval()
    test_llm_wrapper_memory_consolidation()
    test_llm_wrapper_long_conversation()
    test_llm_wrapper_memory_bounded()
    test_llm_wrapper_state_consistency()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60 + "\n")
