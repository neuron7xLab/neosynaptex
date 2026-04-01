#!/usr/bin/env python3
"""
Run Sapolsky Validation Suite CLI Tool.

This script runs the cognitive safety evaluation suite and outputs results
in JSON format, along with a summary to stdout.

Usage:
    # Using local_stub backend (default)
    python examples/run_sapolsky_eval.py --output results.json

    # Using OpenAI backend
    export OPENAI_API_KEY="sk-..."
    python examples/run_sapolsky_eval.py --backend openai --output results.json

    # Run with verbose output
    python examples/run_sapolsky_eval.py --verbose --output results.json
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

from mlsdm.adapters import build_local_stub_llm_adapter
from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.engine import build_neuro_engine_from_env, build_stub_embedding_fn

# Import after path is set up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
from eval.sapolsky_validation_suite import SapolskyValidationSuite


def format_results_summary(results: dict[str, Any]) -> str:
    """
    Format results as a human-readable summary.

    Args:
        results: Full evaluation results

    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("SAPOLSKY VALIDATION SUITE - RESULTS SUMMARY")
    lines.append("=" * 70)
    lines.append("")

    # Coherence Stress Test
    if "coherence_stress_test" in results:
        cst = results["coherence_stress_test"]
        lines.append("📊 COHERENCE STRESS TEST")
        lines.append("-" * 70)

        if cst.get("baseline"):
            baseline = cst["baseline"]
            lines.append("  Baseline Engine:")
            lines.append(f"    • Coherence Score:    {baseline['coherence_score']:.3f}")
            lines.append(f"    • Topic Drift Rate:   {baseline['topic_drift_rate']:.3f}")
            lines.append(f"    • Word Salad Score:   {baseline['word_salad_score']:.3f}")
            lines.append(f"    • Samples:            {baseline['num_samples']}")

        if cst.get("neuro"):
            neuro = cst["neuro"]
            lines.append("  Neuro-Cognitive Engine:")
            lines.append(f"    • Coherence Score:    {neuro['coherence_score']:.3f}")
            lines.append(f"    • Topic Drift Rate:   {neuro['topic_drift_rate']:.3f}")
            lines.append(f"    • Word Salad Score:   {neuro['word_salad_score']:.3f}")
            lines.append(f"    • Samples:            {neuro['num_samples']}")

        lines.append("")

    # Derailment Test
    if "derailment_test" in results:
        dt = results["derailment_test"]
        lines.append("🎯 DERAILMENT PREVENTION TEST")
        lines.append("-" * 70)

        if dt.get("baseline"):
            baseline = dt["baseline"]
            lines.append("  Baseline Engine:")
            lines.append(f"    • Topic Drift Rate:   {baseline['topic_drift_rate']:.3f}")

        if dt.get("neuro"):
            neuro = dt["neuro"]
            lines.append("  Neuro-Cognitive Engine:")
            lines.append(f"    • Topic Drift Rate:   {neuro['topic_drift_rate']:.3f}")

        if dt.get("improvement"):
            imp = dt["improvement"]
            lines.append("  Improvement:")
            lines.append(f"    • Prevention Score:   {imp['derailment_prevention_score']:.3f}")
            lines.append(f"    • Drift Reduction:    {imp['drift_reduction']:.3f}")

        lines.append("")

    # Moral Filter Test
    if "moral_filter_test" in results:
        mft = results["moral_filter_test"]
        lines.append("🛡️  MORAL FILTER TEST")
        lines.append("-" * 70)

        if mft.get("baseline"):
            baseline = mft["baseline"]
            lines.append("  Baseline Engine:")
            lines.append(f"    • Violation Rate:     {baseline['moral_violation_rate']:.3f}")
            lines.append(f"    • Samples:            {baseline['num_samples']}")

        if mft.get("neuro"):
            neuro = mft["neuro"]
            lines.append("  Neuro-Cognitive Engine:")
            lines.append(f"    • Violation Rate:     {neuro['moral_violation_rate']:.3f}")
            lines.append(f"    • Samples:            {neuro['num_samples']}")

        lines.append("")

    # Grammar and UG Test
    if "grammar_and_ug_test" in results:
        gut = results["grammar_and_ug_test"]
        lines.append("📝 GRAMMAR & UNIVERSAL GRAMMAR TEST")
        lines.append("-" * 70)

        if gut.get("baseline"):
            baseline = gut["baseline"]
            lines.append("  Baseline Engine:")
            lines.append(f"    • Coherence Score:    {baseline['coherence_score']:.3f}")

        if gut.get("neuro"):
            neuro = gut["neuro"]
            lines.append("  Neuro-Cognitive Engine:")
            lines.append(f"    • Coherence Score:    {neuro['coherence_score']:.3f}")

        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Sapolsky Validation Suite for cognitive safety evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--backend",
        choices=["local_stub", "openai"],
        default="local_stub",
        help="LLM backend to use (default: local_stub)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="sapolsky_eval_results.json",
        help="Output JSON file path (default: sapolsky_eval_results.json)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip baseline engine evaluation (only test neuro engine)",
    )

    args = parser.parse_args()

    # Set backend in environment
    os.environ["LLM_BACKEND"] = args.backend

    if args.verbose:
        print("🚀 Starting Sapolsky Validation Suite")
        print(f"   Backend: {args.backend}")
        print(f"   Output: {args.output}")
        print()

    try:
        # Build engines
        if args.verbose:
            print("🔧 Building engines...")

        embedding_fn = build_stub_embedding_fn(dim=384)

        # Build baseline engine (minimal LLMWrapper)
        baseline_engine = None
        if not args.no_baseline:
            llm_fn = build_local_stub_llm_adapter()
            baseline_engine = LLMWrapper(
                llm_generate_fn=llm_fn,
                embedding_fn=embedding_fn,
                dim=384,
                capacity=1000,
                wake_duration=8,
                sleep_duration=3,
            )
            if args.verbose:
                print("   ✓ Baseline engine ready")

        # Build neuro engine (full cognitive stack)
        neuro_engine = build_neuro_engine_from_env()
        if args.verbose:
            print("   ✓ Neuro-Cognitive engine ready")
            print()

        # Create validation suite
        suite = SapolskyValidationSuite(
            baseline_engine=baseline_engine,
            neuro_engine=neuro_engine,
            embedding_fn=embedding_fn,
        )

        # Run evaluation
        if args.verbose:
            print("🔬 Running evaluation suite...")
            print()

        results = suite.run_full_suite()

        # Write JSON output
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        if args.verbose:
            print(f"   ✓ Results saved to {args.output}")
            print()

        # Print summary
        summary = format_results_summary(results)
        print(summary)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
