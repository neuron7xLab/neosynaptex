#!/usr/bin/env python3
"""
NeuroCognitiveEngine CLI Demo

This script demonstrates the NeuroCognitiveEngine through a command-line interface.
It supports different LLM backends and allows testing the complete pipeline.

Usage:
    # Using local stub (default, no API key needed)
    python examples/neuro_engine_cli_demo.py --prompt "Hello, world!"

    # Using OpenAI (requires API key)
    export OPENAI_API_KEY="sk-..."
    python examples/neuro_engine_cli_demo.py --backend openai --prompt "Hello!"

    # Reading from stdin
    echo "Tell me about cognitive architectures" | python examples/neuro_engine_cli_demo.py

    # Interactive mode
    python examples/neuro_engine_cli_demo.py --interactive
"""

import argparse
import json
import os
import sys
from typing import Any

# For standalone execution when not installed as package
if __name__ == "__main__":
    # Add src to path only when running as script
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mlsdm.engine import NeuroEngineConfig, build_neuro_engine_from_env


def format_timing(timing: dict[str, float]) -> str:
    """Format timing metrics for display."""
    lines = ["⏱  Timing Metrics:"]
    for key, value in timing.items():
        lines.append(f"  - {key}: {value:.2f} ms")
    return "\n".join(lines)


def format_validation_steps(steps: list[dict[str, Any]]) -> str:
    """Format validation steps for display."""
    if not steps:
        return "✓ No validation steps recorded"

    lines = ["✓ Validation Steps:"]
    for step in steps:
        step_name = step.get("step", "unknown")
        passed = step.get("passed", False)
        status = "✓" if passed else "✗"
        lines.append(f"  {status} {step_name}")

        # Add additional details if present
        if "score" in step:
            lines.append(f"    Score: {step['score']:.3f}")
        if "threshold" in step:
            lines.append(f"    Threshold: {step['threshold']:.3f}")
        if "skipped" in step and step["skipped"]:
            lines.append(f"    (Skipped: {step.get('reason', 'unknown')})")

    return "\n".join(lines)


def format_error(error: dict[str, Any] | None) -> str:
    """Format error information for display."""
    if error is None:
        return "✓ No errors"

    error_type = error.get("type", "unknown")
    message = error.get("message", "No message")
    return f"✗ Error: {error_type}\n  Message: {message}"


def process_request(
    engine: Any,
    prompt: str,
    max_tokens: int,
    moral: float,
    intent: str,
    verbose: bool = False,
) -> None:
    """
    Process a single request and display results.

    Args:
        engine: The NeuroCognitiveEngine instance.
        prompt: The input prompt.
        max_tokens: Maximum tokens to generate.
        moral: Moral threshold value.
        intent: User intent category.
        verbose: Whether to display verbose output.
    """
    print(f"\n{'=' * 80}")
    print(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"{'=' * 80}\n")

    # Generate response
    result = engine.generate(
        prompt=prompt,
        max_tokens=max_tokens,
        moral_value=moral,
        user_intent=intent,
    )

    # Display response
    if result["response"]:
        print("💬 Response:")
        print("-" * 80)
        print(result["response"])
        print("-" * 80)
    else:
        print("⚠️  No response generated")

    # Display rejection info if present
    if result["rejected_at"]:
        print(f"\n🚫 Request rejected at: {result['rejected_at']}")

    # Display error if present
    print(f"\n{format_error(result['error'])}")

    # Display timing
    print(f"\n{format_timing(result['timing'])}")

    # Display validation steps if verbose
    if verbose:
        print(f"\n{format_validation_steps(result['validation_steps'])}")

    # Display JSON output if verbose
    if verbose:
        print("\n📊 Full Result (JSON):")
        # Create serializable version
        serializable = {
            "response": result["response"],
            "timing": result["timing"],
            "validation_steps": result["validation_steps"],
            "error": result["error"],
            "rejected_at": result["rejected_at"],
        }
        print(json.dumps(serializable, indent=2))


def interactive_mode(
    engine: Any,
    max_tokens: int,
    moral: float,
    intent: str,
    verbose: bool,
) -> None:
    """
    Run in interactive mode, processing prompts from user input.

    Args:
        engine: The NeuroCognitiveEngine instance.
        max_tokens: Maximum tokens to generate.
        moral: Moral threshold value.
        intent: User intent category.
        verbose: Whether to display verbose output.
    """
    print("🧠 NeuroCognitiveEngine Interactive Mode")
    print("=" * 80)
    print("Type your prompts below. Use Ctrl+D (Unix) or Ctrl+Z (Windows) to exit.")
    print("=" * 80)

    while True:
        try:
            print("\n> ", end="", flush=True)
            prompt = input()

            if not prompt.strip():
                print("⚠️  Empty prompt, skipping...")
                continue

            process_request(engine, prompt, max_tokens, moral, intent, verbose)

        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NeuroCognitiveEngine CLI Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local stub backend (default)
  python examples/neuro_engine_cli_demo.py --prompt "Hello!"

  # OpenAI backend
  export OPENAI_API_KEY="sk-..."
  python examples/neuro_engine_cli_demo.py --backend openai --prompt "Hello!"

  # From stdin
  echo "Tell me a story" | python examples/neuro_engine_cli_demo.py

  # Interactive mode
  python examples/neuro_engine_cli_demo.py --interactive
        """,
    )

    parser.add_argument(
        "--backend",
        choices=["openai", "local_stub"],
        default="local_stub",
        help="LLM backend to use (default: local_stub)",
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="Input prompt (if not provided, reads from stdin or enters interactive mode)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate (default: 512)",
    )

    parser.add_argument(
        "--moral",
        type=float,
        default=0.5,
        help="Moral threshold value (0.0-1.0, default: 0.5)",
    )

    parser.add_argument(
        "--intent",
        type=str,
        default="conversational",
        help="User intent category (default: conversational)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display verbose output including validation steps and JSON",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    parser.add_argument(
        "--disable-fslgs",
        action="store_true",
        help="Disable FSLGS layer (use only MLSDM)",
    )

    args = parser.parse_args()

    # Set backend environment variable
    os.environ["LLM_BACKEND"] = args.backend

    # Build engine configuration
    config = None
    if args.disable_fslgs:
        config = NeuroEngineConfig(enable_fslgs=False)

    # Build engine
    print("🚀 Initializing NeuroCognitiveEngine...")
    print(f"   Backend: {args.backend}")
    print(f"   Max Tokens: {args.max_tokens}")
    print(f"   Moral Threshold: {args.moral}")
    print(f"   Intent: {args.intent}")
    if config:
        print(f"   FSLGS: {'Disabled' if not config.enable_fslgs else 'Enabled'}")

    try:
        engine = build_neuro_engine_from_env(config=config)
    except Exception as e:
        print(f"\n❌ Error initializing engine: {e}", file=sys.stderr)
        sys.exit(1)

    # Process input
    if args.interactive:
        # Interactive mode
        interactive_mode(engine, args.max_tokens, args.moral, args.intent, args.verbose)
    elif args.prompt:
        # Direct prompt
        process_request(engine, args.prompt, args.max_tokens, args.moral, args.intent, args.verbose)
    else:
        # Read from stdin
        print("📖 Reading prompt from stdin...")
        try:
            prompt = sys.stdin.read().strip()
            if not prompt:
                print("⚠️  No input provided", file=sys.stderr)
                sys.exit(1)
            process_request(engine, prompt, args.max_tokens, args.moral, args.intent, args.verbose)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
