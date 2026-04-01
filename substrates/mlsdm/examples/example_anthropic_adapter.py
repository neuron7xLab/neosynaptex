#!/usr/bin/env python3
"""
Anthropic Adapter Example for MLSDM.

This example demonstrates how to integrate Anthropic's Claude models
with MLSDM's cognitive governance using the build_anthropic_llm_adapter function.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/example_anthropic_adapter.py

Prerequisites:
    pip install -e .
    pip install anthropic

Note:
    This example requires a valid Anthropic API key.
    If you don't have one, use the local_stub backend instead:
    python examples/example_basic_sdk.py
"""

import os
import sys

from mlsdm import create_llm_wrapper
from mlsdm.adapters import build_anthropic_llm_adapter


def check_api_key():
    """Check if Anthropic API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("\nTo run this example:")
        print("1. Get an API key from https://console.anthropic.com/")
        print("2. Export it: export ANTHROPIC_API_KEY='sk-ant-...'")
        print("3. Run this script again")
        print("\nAlternatively, use the local stub example:")
        print("   python examples/example_basic_sdk.py")
        sys.exit(1)


def example_anthropic_basic():
    """Basic example using Anthropic adapter."""
    print("=" * 60)
    print("Example: Anthropic Integration with MLSDM")
    print("=" * 60)

    # Build Anthropic adapter
    try:
        llm_fn = build_anthropic_llm_adapter()
        print("✓ Successfully initialized Anthropic adapter")
        print(f"  Model: {os.environ.get('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')}")
    except Exception as e:
        print(f"✗ Failed to initialize Anthropic adapter: {e}")
        sys.exit(1)

    # Create governed wrapper with Anthropic
    wrapper = create_llm_wrapper(
        llm_generate_fn=llm_fn,
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.5,
    )

    # Generate a response
    prompt = "Explain the concept of emergent behavior in AI systems in 2-3 sentences."
    print(f"\nPrompt: {prompt}")
    print("\nGenerating response with cognitive governance...")

    try:
        result = wrapper.generate(
            prompt=prompt,
            moral_value=0.8,
            max_tokens=256,
        )

        if result["accepted"]:
            print("\n✓ Response accepted (moral threshold check passed)")
            print(f"  Phase: {result['phase']}")
            print(f"  Moral threshold: {result['moral_threshold']:.2f}")
            print("\nClaude's Response:")
            print(f"  {result['response']}\n")
        else:
            print("\n✗ Response rejected by moral filter")
            print(f"  Reason: {result.get('note', 'Unknown')}")

    except Exception as e:
        print(f"\n✗ Error during generation: {e}")
        sys.exit(1)

    # Show system state
    state = wrapper.get_state()
    print("System State:")
    print(f"  Current step: {state['step']}")
    print(f"  Phase: {state['phase']}")
    print(f"  Memory used: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")


def example_anthropic_conversation():
    """Example of a multi-turn conversation."""
    print("\n" + "=" * 60)
    print("Example: Multi-turn conversation with Claude")
    print("=" * 60)

    llm_fn = build_anthropic_llm_adapter()
    wrapper = create_llm_wrapper(llm_generate_fn=llm_fn)

    # Response preview length for output formatting
    RESPONSE_PREVIEW_LENGTH = 150

    conversation = [
        ("What is cognitive architecture?", 0.9),
        ("How does it relate to AI safety?", 0.85),
        ("Give a practical example", 0.8),
    ]

    for i, (prompt, moral_value) in enumerate(conversation, 1):
        print(f"\nTurn {i}: {prompt}")

        result = wrapper.generate(
            prompt=prompt,
            moral_value=moral_value,
            max_tokens=RESPONSE_PREVIEW_LENGTH,
        )

        if result["accepted"]:
            response_preview = (
                result["response"][:RESPONSE_PREVIEW_LENGTH] + "..."
                if len(result["response"]) > RESPONSE_PREVIEW_LENGTH
                else result["response"]
            )
            print(f"Claude: {response_preview}")
        else:
            print(f"[Rejected: {result.get('note')}]")


def main():
    """Run all examples."""
    check_api_key()

    try:
        example_anthropic_basic()
        example_anthropic_conversation()

        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
