#!/usr/bin/env python3
"""
Run Aphasia-Broca evaluation suite.

This script runs the AphasiaEvalSuite to evaluate the detection
performance on a corpus of telegraphic and normal speech samples.

Usage:
    python scripts/run_aphasia_eval.py --corpus tests/eval/aphasia_corpus.json
"""

import argparse
import sys
from pathlib import Path

# Add src and tests/eval to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "eval"))

from aphasia_eval_suite import AphasiaEvalSuite


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run Aphasia-Broca evaluation suite.")
    parser.add_argument(
        "--corpus",
        type=str,
        default="tests/eval/aphasia_corpus.json",
        help="Path to aphasia corpus JSON (default: tests/eval/aphasia_corpus.json)",
    )
    parser.add_argument(
        "--fail-on-low-metrics",
        action="store_true",
        help="Exit with non-zero code if metrics are below recommended thresholds.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    corpus_path = Path(args.corpus)

    if not corpus_path.exists():
        print(f"Error: Corpus file not found: {corpus_path}")
        return 1

    suite = AphasiaEvalSuite(corpus_path=corpus_path)
    result = suite.run()

    print("AphasiaEvalSuite metrics:")
    print(f"  true_positive_rate:        {result.true_positive_rate:.3f}")
    print(f"  true_negative_rate:        {result.true_negative_rate:.3f}")
    print(f"  mean_severity_telegraphic: {result.mean_severity_telegraphic:.3f}")
    print(f"  telegraphic_samples:       {result.telegraphic_samples}")
    print(f"  normal_samples:            {result.normal_samples}")

    if args.fail_on_low_metrics:
        if (
            result.true_positive_rate < 0.8
            or result.true_negative_rate < 0.8
            or result.mean_severity_telegraphic < 0.3
        ):
            print("\n⚠ Warning: Metrics below recommended thresholds!")
            return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
