"""Run automated performance profiling for MLSDM benchmarks."""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from tests.benchmarks.compare_baselines import (
    BenchmarkSuite,
    FullMLSDM,
    SimpleRAG,
    StatelessMode,
    VectorDBOnly,
    mock_embedding_fn,
    mock_llm_generate,
)


def build_suite(num_requests: int) -> BenchmarkSuite:
    """Create and run the benchmark suite."""
    suite = BenchmarkSuite()
    suite.register_baseline("Simple RAG", SimpleRAG(mock_llm_generate, mock_embedding_fn))
    suite.register_baseline("Vector DB Only", VectorDBOnly(mock_llm_generate, mock_embedding_fn))
    suite.register_baseline("Stateless Mode", StatelessMode(mock_llm_generate, mock_embedding_fn))
    suite.register_baseline("Full MLSDM", FullMLSDM(mock_llm_generate, mock_embedding_fn))

    suite.run_latency_benchmark(num_requests=num_requests)
    suite.run_toxicity_benchmark()
    suite.run_coherence_benchmark()
    return suite


def extract_top_functions(stats: pstats.Stats, limit: int) -> list[dict[str, Any]]:
    """Extract top functions by cumulative time."""
    entries = sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)
    top_entries = entries[:limit]
    summary: list[dict[str, Any]] = []

    for (filename, line_no, func_name), (cc, nc, tt, ct, _callers) in top_entries:
        summary.append(
            {
                "file": filename,
                "line": line_no,
                "function": func_name,
                "callcount": nc,
                "primitive_calls": cc,
                "total_time_s": tt,
                "cumulative_time_s": ct,
            }
        )

    return summary


def write_profile_summary(
    stats: pstats.Stats, output_path: Path, num_requests: int, top_n: int
) -> None:
    """Write JSON summary for profiling results."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "num_requests": num_requests,
        "top_functions": extract_top_functions(stats, top_n),
    }
    output_path.write_text(json.dumps(summary, indent=2))


def write_profile_text(stats: pstats.Stats, output_path: Path, top_n: int) -> None:
    """Write text summary for profiling results."""
    buffer = StringIO()
    stats.sort_stats(pstats.SortKey.CUMULATIVE)
    stats.stream = buffer
    stats.print_stats(top_n)
    output_path.write_text(buffer.getvalue())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MLSDM performance profiling.")
    parser.add_argument(
        "--output-dir",
        default="reports/profiling",
        help="Directory to store profiling artifacts.",
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=25,
        help="Number of requests per baseline for latency profiling.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top functions to include in summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile_path = output_dir / "performance_profile.pstats"
    report_path = output_dir / "baseline_comparison_report.json"
    summary_json_path = output_dir / "performance_profile_summary.json"
    summary_text_path = output_dir / "performance_profile_summary.txt"

    profiler = cProfile.Profile()
    profiler.enable()
    suite = build_suite(num_requests=args.num_requests)
    profiler.disable()

    suite.generate_report(output_path=str(report_path))

    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.dump_stats(str(profile_path))

    write_profile_summary(stats, summary_json_path, args.num_requests, args.top_n)
    write_profile_text(stats, summary_text_path, args.top_n)

    print("Profiling artifacts written to:")
    print(f"  - {profile_path}")
    print(f"  - {report_path}")
    print(f"  - {summary_json_path}")
    print(f"  - {summary_text_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
