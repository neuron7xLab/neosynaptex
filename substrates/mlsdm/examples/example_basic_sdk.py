#!/usr/bin/env python3
"""
Basic SDK Example for MLSDM.

This example demonstrates how to use the MLSDM SDK client to generate
governed responses using the NeuroCognitiveClient.

Usage:
    python examples/example_basic_sdk.py

Prerequisites:
    pip install -e .
"""

from mlsdm import NeuroCognitiveClient, create_llm_wrapper, create_neuro_engine


def example_neuro_cognitive_client():
    """Example using NeuroCognitiveClient (high-level SDK)."""
    print("=" * 60)
    print("Example 1: NeuroCognitiveClient")
    print("=" * 60)

    # Initialize client with local stub backend (no API key needed)
    client = NeuroCognitiveClient(backend="local_stub")

    # Generate a response
    result = client.generate(
        prompt="What is consciousness?",
        max_tokens=256,
        moral_value=0.8,
    )

    print("\nPrompt: What is consciousness?")
    print(f"Response: {result['response'][:200]}...")
    print(f"Phase: {result.get('mlsdm', {}).get('phase', 'unknown')}")
    print(f"Timing: {result.get('timing', {}).get('total', 0):.2f}ms")


def example_llm_wrapper():
    """Example using LLMWrapper (low-level API)."""
    print("\n" + "=" * 60)
    print("Example 2: LLMWrapper")
    print("=" * 60)

    # Create wrapper with default stub LLM
    wrapper = create_llm_wrapper(
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Generate with governance
    result = wrapper.generate(
        prompt="Explain quantum computing",
        moral_value=0.85,
    )

    print("\nPrompt: Explain quantum computing")
    print(f"Accepted: {result['accepted']}")
    print(f"Phase: {result['phase']}")
    print(f"Response: {result['response'][:200]}...")

    # Get system state
    state = wrapper.get_state()
    print("\nSystem State:")
    print(f"  Step: {state['step']}")
    print(f"  Moral Threshold: {state['moral_threshold']:.2f}")
    print(f"  Memory Used: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")


def example_neuro_engine():
    """Example using NeuroCognitiveEngine."""
    print("\n" + "=" * 60)
    print("Example 3: NeuroCognitiveEngine")
    print("=" * 60)

    # Create engine with defaults
    engine = create_neuro_engine()

    # Generate governed response
    result = engine.generate(
        prompt="Tell me about machine learning",
        max_tokens=256,
        moral_value=0.9,
    )

    print("\nPrompt: Tell me about machine learning")
    print(f"Response: {result['response'][:200]}...")

    # Access MLSDM state
    mlsdm_state = result.get("mlsdm", {})
    print(f"Phase: {mlsdm_state.get('phase', 'unknown')}")
    print(f"Moral Threshold: {mlsdm_state.get('moral_threshold', 0):.2f}")


def example_moral_filtering():
    """Example demonstrating moral filtering behavior."""
    print("\n" + "=" * 60)
    print("Example 4: Moral Filtering")
    print("=" * 60)

    wrapper = create_llm_wrapper(initial_moral_threshold=0.6)

    test_cases = [
        ("High moral value (0.9)", 0.9),
        ("Medium moral value (0.7)", 0.7),
        ("Low moral value (0.4)", 0.4),
    ]

    for description, moral_value in test_cases:
        result = wrapper.generate(
            prompt="Test prompt",
            moral_value=moral_value,
        )
        status = "✓ Accepted" if result["accepted"] else "✗ Rejected"
        print(f"  {description}: {status}")

    print(f"\nFinal moral threshold: {wrapper.get_state()['moral_threshold']:.2f}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MLSDM SDK Examples")
    print("=" * 60)

    example_neuro_cognitive_client()
    example_llm_wrapper()
    example_neuro_engine()
    example_moral_filtering()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - See SDK_USAGE.md for detailed documentation")
    print("  - Run 'mlsdm serve' to start the HTTP API")
    print("  - See example_http_client.py for HTTP examples")
    print("=" * 60 + "\n")
