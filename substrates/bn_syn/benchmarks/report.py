#!/usr/bin/env python3
"""Generate Markdown benchmark reports from CSV/JSON results.

Usage:
    python benchmarks/report.py --input results/bench.csv --output docs/benchmarks/README.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_results(input_path: str) -> list[dict[str, Any]]:
    """Load benchmark results from CSV or JSON."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if path.suffix == ".json":
        with open(path) as f:
            return json.load(f)
    elif path.suffix == ".csv":
        with open(path) as f:
            reader = csv.DictReader(f)
            results = []
            for row in reader:
                # Convert numeric fields
                for key in row:
                    if key in [
                        "seed",
                        "steps",
                        "N_neurons",
                        "repeats",
                        "spike_count_total",
                    ]:
                        row[key] = int(float(row[key]))
                    elif key in [
                        "dt_ms",
                        "p_conn",
                        "frac_inhib",
                        "wall_time_sec_mean",
                        "wall_time_sec_p50",
                        "wall_time_sec_p95",
                        "wall_time_sec_std",
                        "peak_rss_mb_mean",
                        "peak_rss_mb_p50",
                        "peak_rss_mb_p95",
                        "peak_rss_mb_std",
                        "per_step_ms_mean",
                        "per_step_ms_p50",
                        "per_step_ms_p95",
                        "per_step_ms_std",
                        "neuron_steps_per_sec_mean",
                        "neuron_steps_per_sec_p50",
                        "neuron_steps_per_sec_p95",
                        "neuron_steps_per_sec_std",
                    ]:
                        row[key] = float(row[key])
                results.append(row)
            return results
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def format_number(val: float, decimals: int = 2) -> str:
    """Format number with thousands separator."""
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"


def generate_markdown_report(results: list[dict[str, Any]]) -> str:
    """Generate Markdown report from results."""
    if not results:
        return "# Benchmark Results\n\nNo results available.\n"

    # Extract metadata
    git_sha = results[0].get("git_sha", "unknown")
    python_ver = results[0].get("python_version", "unknown")
    timestamp = results[0].get("timestamp", "unknown")

    md = ["# BN-Syn Benchmark Results\n"]
    md.append(f"**Generated:** {timestamp}\n")
    md.append(f"**Git SHA:** `{git_sha[:8]}`\n")
    md.append(f"**Python:** {python_ver}\n")
    md.append("\n## Summary Table\n")

    # Summary table
    md.append(
        "| Scenario | N | Steps | dt (ms) | Time (s) | RSS (MB) | Throughput (neuron-steps/s) |\n"
    )
    md.append(
        "|----------|---|-------|---------|----------|----------|------------------------------|\n"
    )

    for r in results:
        scenario = r["scenario"]
        n = format_number(r["N_neurons"], 0)
        steps = format_number(r["steps"], 0)
        dt = f"{r['dt_ms']:.2f}"
        time_mean = f"{r['wall_time_sec_mean']:.2f}"
        rss_mean = f"{r['peak_rss_mb_mean']:.1f}"
        throughput = format_number(r["neuron_steps_per_sec_mean"], 0)
        md.append(
            f"| {scenario} | {n} | {steps} | {dt} | {time_mean} | {rss_mean} | {throughput} |\n"
        )

    md.append("\n## Detailed Metrics\n")

    # Detailed metrics per scenario
    for r in results:
        md.append(f"### {r['scenario']}\n")
        md.append(f"**Description:** {r.get('description', 'N/A')}\n")
        md.append("\n**Parameters:**\n")
        md.append(f"- N_neurons: {format_number(r['N_neurons'], 0)}\n")
        md.append(f"- steps: {format_number(r['steps'], 0)}\n")
        md.append(f"- dt_ms: {r['dt_ms']}\n")
        md.append(f"- p_conn: {r['p_conn']}\n")
        md.append(f"- frac_inhib: {r['frac_inhib']}\n")
        md.append(f"- seed: {r['seed']}\n")
        md.append(f"- repeats: {r['repeats']}\n")
        md.append("\n**Timing:**\n")
        md.append(
            f"- wall_time: {r['wall_time_sec_mean']:.3f}s "
            f"(p50={r['wall_time_sec_p50']:.3f}, p95={r['wall_time_sec_p95']:.3f}, "
            f"std={r['wall_time_sec_std']:.3f})\n"
        )
        md.append(
            f"- per_step: {r['per_step_ms_mean']:.3f}ms "
            f"(p50={r['per_step_ms_p50']:.3f}, p95={r['per_step_ms_p95']:.3f}, "
            f"std={r['per_step_ms_std']:.3f})\n"
        )
        md.append("\n**Memory:**\n")
        md.append(
            f"- peak_rss: {r['peak_rss_mb_mean']:.1f}MB "
            f"(p50={r['peak_rss_mb_p50']:.1f}, p95={r['peak_rss_mb_p95']:.1f}, "
            f"std={r['peak_rss_mb_std']:.1f})\n"
        )
        md.append("\n**Throughput:**\n")
        md.append(
            f"- neuron_steps/sec: {format_number(r['neuron_steps_per_sec_mean'], 0)} "
            f"(p50={format_number(r['neuron_steps_per_sec_p50'], 0)}, "
            f"p95={format_number(r['neuron_steps_per_sec_p95'], 0)}, "
            f"std={format_number(r['neuron_steps_per_sec_std'], 0)})\n"
        )
        md.append("\n**Activity:**\n")
        md.append(f"- spike_count_total: {format_number(r['spike_count_total'], 0)}\n")
        md.append("\n")

    md.append("---\n")
    md.append(
        "*This report is auto-generated from benchmark results. "
        "See [PROTOCOL.md](PROTOCOL.md) for reproducibility details.*\n"
    )

    return "".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate benchmark report")
    parser.add_argument("--input", required=True, help="Input CSV or JSON file")
    parser.add_argument("--output", required=True, help="Output Markdown file")

    args = parser.parse_args()

    try:
        results = load_results(args.input)
        report = generate_markdown_report(results)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)

        print(f"Generated report: {args.output}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
