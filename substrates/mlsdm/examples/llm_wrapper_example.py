"""
Example: Using LLMWrapper with a real or mock LLM

This example demonstrates how to integrate the MLSDM Governed Cognitive Memory
wrapper with any LLM to enforce biological constraints and maintain coherence.

The wrapper provides:
1. Hard memory limits (20k vectors, ≤1.4 GB RAM)
2. Adaptive moral homeostasis
3. Circadian rhythm with wake/sleep cycles
4. Multi-level synaptic memory
5. Phase-entangling retrieval
"""

import os
import sys

import numpy as np

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mlsdm.core.llm_wrapper import LLMWrapper

# =============================================================================
# Example 1: Simple Mock LLM
# =============================================================================


def simple_mock_llm(prompt: str, max_tokens: int) -> str:
    """
    Simple mock LLM for demonstration.
    Replace this with your actual LLM (OpenAI, Anthropic, local model, etc.)
    """
    responses = {
        "hello": "Hello! How can I assist you today?",
        "python": "Python is a versatile programming language great for AI and data science.",
        "code": "Here's an example:\n\n```python\nprint('Hello, World!')\n```",
        "memory": "I use a cognitive memory system with wake/sleep cycles for optimal performance.",
    }

    prompt_lower = prompt.lower()
    for key, response in responses.items():
        if key in prompt_lower:
            return response

    return "I understand your question. Let me help you with that."


def simple_mock_embedding(text: str) -> np.ndarray:
    """
    Simple mock embedding function.
    Replace this with your actual embedding model (sentence-transformers, OpenAI, etc.)
    """
    # For demonstration, create deterministic embeddings based on text hash
    seed = sum(ord(c) for c in text) % (2**32)
    np.random.seed(seed)
    vec = np.random.randn(384).astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / (norm + 1e-9)


def example_1_basic_usage():
    """Example 1: Basic usage with mock LLM."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Usage")
    print("=" * 70)

    # Initialize wrapper
    wrapper = LLMWrapper(
        llm_generate_fn=simple_mock_llm,
        embedding_fn=simple_mock_embedding,
        dim=384,
        capacity=20_000,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.50,
    )

    # Simulate conversation
    messages = [
        ("Hello! Can you help me?", 0.95),
        ("Tell me about Python programming", 0.90),
        ("Can you show me some code examples?", 0.85),
        ("What's your memory system like?", 0.90),
    ]

    for i, (prompt, moral_value) in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"User: {prompt}")
        print(f"Moral Value: {moral_value}")

        result = wrapper.generate(prompt, moral_value)

        print(f"Accepted: {result['accepted']}")
        print(f"Phase: {result['phase']}")

        if result["accepted"]:
            print(f"Assistant: {result['response']}")
            print(f"Context Items: {result['context_items']}")
        else:
            print(f"Note: {result['note']}")

        print(f"Moral Threshold: {result['moral_threshold']}")

    # Print final state
    print("\n" + "-" * 70)
    state = wrapper.get_state()
    print("Final State:")
    print(f"  Steps: {state['step']}")
    print(f"  Phase: {state['phase']}")
    print(f"  Accepted: {state['accepted_count']}")
    print(f"  Rejected: {state['rejected_count']}")
    print(f"  Memory Used: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")
    print(f"  Memory MB: {state['qilm_stats']['memory_mb']}")


# =============================================================================
# Example 2: With Moral Filtering
# =============================================================================


def example_2_moral_filtering():
    """Example 2: Demonstrate moral filtering."""
    print("\n" + "=" * 70)
    print("Example 2: Moral Filtering")
    print("=" * 70)

    wrapper = LLMWrapper(
        llm_generate_fn=simple_mock_llm,
        embedding_fn=simple_mock_embedding,
        initial_moral_threshold=0.70,  # Higher threshold = stricter
    )

    # Test various moral values
    test_cases = [
        ("Tell me something nice", 0.95, "High moral - should accept"),
        ("Neutral question", 0.75, "Medium moral - should accept"),
        ("Questionable content", 0.65, "Below threshold - should reject"),
        ("Very low moral value", 0.20, "Very low - definitely reject"),
    ]

    for prompt, moral_value, description in test_cases:
        print(f"\n{description}")
        print(f"  Prompt: {prompt}")
        print(f"  Moral Value: {moral_value}")

        result = wrapper.generate(prompt, moral_value)

        if result["accepted"]:
            print(f"  ✅ ACCEPTED - Response: {result['response'][:50]}...")
        else:
            print(f"  ❌ REJECTED - {result['note']}")

        print(f"  Threshold: {result['moral_threshold']}")


# =============================================================================
# Example 3: Wake/Sleep Cycles
# =============================================================================


def example_3_wake_sleep_cycles():
    """Example 3: Demonstrate wake/sleep cycle behavior."""
    print("\n" + "=" * 70)
    print("Example 3: Wake/Sleep Cycles")
    print("=" * 70)

    wrapper = LLMWrapper(
        llm_generate_fn=simple_mock_llm,
        embedding_fn=simple_mock_embedding,
        wake_duration=3,  # Short for demo
        sleep_duration=2,
    )

    print("\nProcessing 10 messages across multiple cycles...")

    for i in range(10):
        result = wrapper.generate(f"Message {i+1}", moral_value=0.9)

        status = "✅ ACCEPTED" if result["accepted"] else "❌ REJECTED"
        phase_emoji = "☀️" if result["phase"] == "wake" else "🌙"

        print(f"{i+1:2d}. {phase_emoji} {result['phase']:5s} | {status:12s} | {result['note']}")

    state = wrapper.get_state()
    print(f"\nFinal: {state['accepted_count']} accepted, {state['rejected_count']} rejected")


# =============================================================================
# Example 4: Memory Consolidation
# =============================================================================


def example_4_memory_consolidation():
    """Example 4: Memory consolidation during sleep."""
    print("\n" + "=" * 70)
    print("Example 4: Memory Consolidation")
    print("=" * 70)

    wrapper = LLMWrapper(
        llm_generate_fn=simple_mock_llm,
        embedding_fn=simple_mock_embedding,
        wake_duration=4,
        sleep_duration=2,
    )

    print("\nBuilding memories during wake phase...")
    topics = ["AI", "Python", "Machine Learning", "Neural Networks"]

    for topic in topics:
        result = wrapper.generate(f"Tell me about {topic}", moral_value=0.9)
        if result["accepted"]:
            print(f"  ✓ Added memory: {topic}")
            state = wrapper.get_state()
            print(
                f"    Buffer: {state['consolidation_buffer_size']}, "
                f"QILM: {state['qilm_stats']['used']}"
            )

    # Advance to sleep phase and trigger consolidation
    print("\nAdvancing to sleep phase...")
    for _ in range(2):
        result = wrapper.generate("Sleep message", moral_value=0.9)
        print(f"  Phase: {result['phase']}, Note: {result['note']}")

    state = wrapper.get_state()
    print("\nConsolidation complete:")
    print(f"  Buffer size: {state['consolidation_buffer_size']}")
    print(f"  QILM used: {state['qilm_stats']['used']}")


# =============================================================================
# Example 5: Integration with Sentence Transformers (Optional)
# =============================================================================


def example_5_real_embeddings():
    """Example 5: Using real sentence transformers (if available)."""
    print("\n" + "=" * 70)
    print("Example 5: Real Embeddings (Optional)")
    print("=" * 70)

    try:
        import importlib.util

        if importlib.util.find_spec("sentence_transformers") is not None:
            print("\n✓ sentence-transformers is installed")

        print("\nℹ️  Skipping model load for CI/demo")
        print("   In production, uncomment the code below:")
        print("   # model = SentenceTransformer('all-MiniLM-L6-v2')")

        # Uncomment for real usage:
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # def real_embedding(text: str) -> np.ndarray:
        #     return model.encode(text, convert_to_numpy=True)
        # wrapper = LLMWrapper(
        #     llm_generate_fn=simple_mock_llm,
        #     embedding_fn=real_embedding,
        #     dim=384
        # )

    except ImportError:
        print("\nℹ️  sentence-transformers not installed")
        print("   Install with: pip install sentence-transformers")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MLSDM Governed Cognitive Memory - LLM Wrapper Examples")
    print("Production-Ready v1.2.0")
    print("=" * 70)

    # Run examples
    example_1_basic_usage()
    example_2_moral_filtering()
    example_3_wake_sleep_cycles()
    example_4_memory_consolidation()
    example_5_real_embeddings()

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Replace mock_llm with your actual LLM (OpenAI, Anthropic, etc.)")
    print("2. Replace mock_embedding with real embeddings (sentence-transformers)")
    print("3. Adjust parameters (wake_duration, moral_threshold) for your use case")
    print("4. Deploy with FastAPI for production use")
    print("\nSee README.md for more information.")
    print("=" * 70 + "\n")
