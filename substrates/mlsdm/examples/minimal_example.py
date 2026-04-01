#!/usr/bin/env python3
"""
Minimal MLSDM Example

This example demonstrates using MLSDM with minimal dependencies.
Works without OpenTelemetry installed.

Installation:
    pip install -e .

Run:
    python examples/minimal_example.py
"""

import importlib.util

import numpy as np

from mlsdm.core.llm_wrapper import LLMWrapper


# 1. Define a simple stub LLM for testing
def stub_llm(prompt: str, max_tokens: int) -> str:
    """Simple stub LLM that echoes the prompt."""
    return f"Stub response to: {prompt[:50]}..."


# 2. Define a simple stub embedder for testing
def stub_embedder(text: str) -> np.ndarray:
    """Simple stub embedder with deterministic random embeddings.

    In production, use sentence-transformers or OpenAI embeddings.
    """
    # Create deterministic embeddings based on text hash
    seed = abs(hash(text)) % (2**32)
    rng = np.random.default_rng(seed)
    return rng.standard_normal(384, dtype=np.float32)


def main():
    print("=" * 60)
    print("MLSDM Minimal Example")
    print("=" * 60)
    print()

    # Check if OpenTelemetry is available
    if importlib.util.find_spec("opentelemetry") is not None:
        print("✓ OpenTelemetry: INSTALLED")
    else:
        print("ℹ OpenTelemetry: NOT INSTALLED (tracing disabled)")
    print()

    # 3. Create the governed wrapper
    print("Creating LLMWrapper with minimal configuration...")
    wrapper = LLMWrapper(
        llm_generate_fn=stub_llm,
        embedding_fn=stub_embedder,
        dim=384,  # Embedding dimension
        capacity=10_000,  # Memory capacity (reduced for demo)
        wake_duration=8,  # Wake phase steps
        sleep_duration=3,  # Sleep phase steps
        initial_moral_threshold=0.50,  # Starting moral threshold
    )
    print("✓ LLMWrapper created successfully")
    print()

    # 4. Generate some responses with different moral values
    test_prompts = [
        ("Explain quantum computing", 0.8),
        ("Describe machine learning", 0.7),
        ("What is cognitive governance?", 0.9),
    ]

    print("Generating responses...")
    print("-" * 60)

    for i, (prompt, moral_value) in enumerate(test_prompts, 1):
        result = wrapper.generate(prompt=prompt, moral_value=moral_value)

        print(f"\n{i}. Prompt: {prompt}")
        print(f"   Moral Value: {moral_value}")
        print(f"   Response: {result['response'][:60]}...")
        print(f"   Accepted: {result['accepted']}")
        print(f"   Phase: {result['phase']}")
        print(f"   Moral Threshold: {result['moral_threshold']:.3f}")

    print()
    print("-" * 60)

    # 5. Check wrapper state
    state = wrapper.get_state()
    print("\nWrapper State:")
    print(f"  Current Phase: {state['phase']}")
    print(f"  Phase Counter: {state['phase_counter']}")
    print(f"  Step: {state['step']}")
    print(f"  Moral Threshold: {state['moral_threshold']:.3f}")
    print(f"  Accepted Count: {state['accepted_count']}")
    print(f"  Rejected Count: {state['rejected_count']}")
    print(f"  PELM Stats: {state['pelm_stats']}")
    print()

    print("=" * 60)
    print("✅ Minimal example completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Replace stub_llm with your actual LLM (OpenAI, Anthropic, etc.)")
    print("  2. Replace stub_embedder with real embeddings (sentence-transformers)")
    print("  3. See GETTING_STARTED.md for more examples")
    print()


if __name__ == "__main__":
    main()
