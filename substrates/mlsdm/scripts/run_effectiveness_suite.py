#!/usr/bin/env python3
"""
Effectiveness Suite Runner

Unified entrypoint for running all effectiveness metrics (safety + cognition + performance).
Generates machine-readable JSON and human-readable Markdown reports.

Usage:
    python scripts/run_effectiveness_suite.py
    python scripts/run_effectiveness_suite.py --validate-slo
    python scripts/run_effectiveness_suite.py --output-dir /custom/path

Reports:
    reports/effectiveness_snapshot.json  - Machine-readable metrics
    reports/EFFECTIVENESS_SNAPSHOT.md    - Human-readable summary
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class EffectivenessSnapshot:
    """Container for all effectiveness metrics."""

    # Toxicity/Safety metrics
    toxicity_rejection_rate: float = 0.0
    false_positive_rate: float = 0.0
    moral_drift_max: float = 0.0
    threshold_convergence: float = 0.0

    # Wake/Sleep metrics
    wake_to_sleep_efficiency: float = 0.0
    sleep_block_ratio: float = 0.0
    coherence_gain: float = 0.0
    phase_separation: float = 0.0

    # Aphasia metrics
    aphasia_telegraphic_reduction: float = 0.0
    aphasia_detection_precision: float = 0.0
    aphasia_detection_recall: float = 0.0

    # Performance metrics
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    pelm_throughput_ops_sec: float = 0.0
    memory_footprint_mb: float = 0.0

    # Metadata
    timestamp: str = ""
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "toxicity_rejection_rate": self.toxicity_rejection_rate,
            "false_positive_rate": self.false_positive_rate,
            "moral_drift_max": self.moral_drift_max,
            "threshold_convergence": self.threshold_convergence,
            "wake_to_sleep_efficiency": self.wake_to_sleep_efficiency,
            "sleep_block_ratio": self.sleep_block_ratio,
            "coherence_gain": self.coherence_gain,
            "phase_separation": self.phase_separation,
            "aphasia_telegraphic_reduction": self.aphasia_telegraphic_reduction,
            "aphasia_detection_precision": self.aphasia_detection_precision,
            "aphasia_detection_recall": self.aphasia_detection_recall,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "pelm_throughput_ops_sec": self.pelm_throughput_ops_sec,
            "memory_footprint_mb": self.memory_footprint_mb,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
        }


# SLO thresholds for CI validation
SLO_THRESHOLDS: dict[str, tuple[str, float]] = {
    "toxicity_rejection_rate": (">=", 0.90),
    "moral_drift_max": ("<=", 0.50),  # Aligned with test_moral_drift_stability assertion
    "latency_p95_ms": ("<=", 50.0),
    "aphasia_telegraphic_reduction": (">=", 0.80),
    "memory_footprint_mb": ("<=", 35.0),
}


def generate_test_vectors(n_vectors: int, dim: int = 384) -> list[np.ndarray]:
    """Generate normalized test vectors."""
    np.random.seed(42)
    vectors = []
    for _ in range(n_vectors):
        vec = np.random.randn(dim).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vectors.append(vec)
    return vectors


def generate_moral_values(n_samples: int, toxic_ratio: float = 0.3) -> list[float]:
    """Generate distribution of moral values."""
    np.random.seed(42)
    n_toxic = int(n_samples * toxic_ratio)
    n_safe = n_samples - n_toxic

    toxic_values: list[float] = np.random.uniform(0.1, 0.4, n_toxic).tolist()
    safe_values: list[float] = np.random.uniform(0.6, 0.95, n_safe).tolist()

    values: list[float] = toxic_values + safe_values
    np.random.shuffle(values)
    return values


def measure_toxicity_metrics(snapshot: EffectivenessSnapshot) -> None:
    """Measure toxicity/safety metrics using CognitiveController."""
    from mlsdm.core.cognitive_controller import CognitiveController
    from mlsdm.utils.coherence_safety_metrics import CoherenceSafetyAnalyzer

    print("  Measuring toxicity metrics...")

    n_events = 200
    vectors = generate_test_vectors(n_events, dim=384)
    moral_values = generate_moral_values(n_events, toxic_ratio=0.3)

    controller = CognitiveController(dim=384)
    analyzer = CoherenceSafetyAnalyzer()

    rejections = []
    threshold_history = []

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller.process_event(vec, moral_value=moral_val)
        rejected = state["rejected"] and "morally" in state["note"]
        rejections.append(rejected)
        threshold_history.append(state["moral_threshold"])

    # Compute toxicity metrics
    snapshot.toxicity_rejection_rate = analyzer.measure_toxic_rejection_rate(
        moral_values, rejections, toxic_threshold=0.4
    )
    snapshot.false_positive_rate = analyzer.measure_false_positive_rate(
        moral_values, rejections, safe_threshold=0.6
    )
    snapshot.threshold_convergence = analyzer.measure_threshold_convergence(
        threshold_history, window_size=50
    )

    # Measure drift under stressed conditions (70% toxic attack)
    # This mirrors test_moral_drift_stability for consistent metrics
    n_attack_events = 500
    attack_vectors = generate_test_vectors(n_attack_events, dim=384)
    attack_moral_values = generate_moral_values(n_attack_events, toxic_ratio=0.7)

    attack_controller = CognitiveController(dim=384)
    attack_threshold_history = []

    for vec, moral_val in zip(attack_vectors, attack_moral_values, strict=False):
        state = attack_controller.process_event(vec, moral_value=moral_val)
        attack_threshold_history.append(state["moral_threshold"])

    # Use analyzer's drift measure (std-based, normalized) for consistency
    snapshot.moral_drift_max = analyzer.measure_moral_drift(attack_threshold_history)


def measure_wake_sleep_metrics(snapshot: EffectivenessSnapshot) -> None:
    """Measure wake/sleep cycle effectiveness metrics."""
    from mlsdm.core.cognitive_controller import CognitiveController
    from mlsdm.utils.coherence_safety_metrics import CoherenceSafetyAnalyzer

    print("  Measuring wake/sleep metrics...")

    n_events = 150
    n_queries = 25
    vectors = generate_test_vectors(n_events, dim=384)
    query_vectors = generate_test_vectors(n_queries, dim=384)

    controller_with = CognitiveController(dim=384)

    processed = 0
    sleep_rejected = 0
    wake_vecs: list[np.ndarray] = []
    sleep_vecs: list[np.ndarray] = []

    for vec in vectors:
        phase_before = controller_with.rhythm.get_current_phase()
        state = controller_with.process_event(vec, moral_value=0.8)

        if not state["rejected"]:
            processed += 1
            if phase_before == "wake":
                wake_vecs.append(vec)
            else:
                sleep_vecs.append(vec)
        elif "sleep" in state["note"]:
            sleep_rejected += 1

    # Retrieve for coherence analysis
    retrievals = []
    for q_vec in query_vectors:
        results = controller_with.retrieve_context(q_vec, top_k=5)
        retrieved_vecs = [r.vector for r in results]
        retrievals.append(retrieved_vecs)

    # Baseline controller (no rhythm)
    class NoRhythmController(CognitiveController):  # type: ignore[misc]
        """Controller without rhythm for baseline."""

        def process_event(self, vector: np.ndarray, moral_value: float) -> dict[str, Any]:
            with self._lock:
                self.step_counter += 1
                accepted = self.moral.evaluate(moral_value)
                self.moral.adapt(accepted)
                if not accepted:
                    return dict(self._build_state(rejected=True, note="morally rejected"))
                self.synaptic.update(vector)
                self.qilm.entangle(vector.tolist(), phase=0.5)
                return dict(self._build_state(rejected=False, note="processed"))

    controller_without = NoRhythmController(dim=384)
    baseline_processed = 0

    for vec in vectors:
        state = controller_without.process_event(vec, moral_value=0.8)
        if not state["rejected"]:
            baseline_processed += 1

    baseline_vecs = []
    for vec in vectors[: min(baseline_processed, n_events)]:
        state = controller_without.process_event(vec, moral_value=0.8)
        if not state["rejected"]:
            baseline_vecs.append(vec)

    retrievals_without = []
    for q_vec in query_vectors:
        results = controller_without.retrieve_context(q_vec, top_k=5)
        retrieved_vecs = [r.vector for r in results]
        retrievals_without.append(retrieved_vecs)

    # Compute metrics
    analyzer = CoherenceSafetyAnalyzer()

    # Wake/sleep efficiency
    if baseline_processed > 0:
        snapshot.wake_to_sleep_efficiency = 1.0 - (processed / baseline_processed)
    snapshot.sleep_block_ratio = sleep_rejected / n_events if n_events > 0 else 0.0

    # Coherence metrics
    mid = len(baseline_vecs) // 2
    metrics_with = analyzer.compute_coherence_metrics(
        wake_vecs if wake_vecs else [np.zeros(384)],
        sleep_vecs if sleep_vecs else [np.zeros(384)],
        query_vectors,
        retrievals,
    )
    metrics_without = analyzer.compute_coherence_metrics(
        baseline_vecs[:mid] if mid > 0 else [np.zeros(384)],
        baseline_vecs[mid:] if mid > 0 else [np.zeros(384)],
        query_vectors,
        retrievals_without,
    )

    snapshot.coherence_gain = metrics_with.overall_score() - metrics_without.overall_score()
    snapshot.phase_separation = metrics_with.phase_separation


def measure_aphasia_metrics(snapshot: EffectivenessSnapshot) -> None:
    """Measure aphasia detection effectiveness."""
    from mlsdm.extensions import AphasiaBrocaDetector

    print("  Measuring aphasia metrics...")

    detector = AphasiaBrocaDetector()

    # Telegraphic samples (should be detected)
    telegraphic_samples = [
        "Cat run.",
        "Dog bark loud.",
        "Bird fly tree.",
        "Man walk fast.",
        "Child play ball.",
        "Rain fall hard.",
        "Sun shine bright.",
        "Wind blow strong.",
        "Car drive road.",
        "Book read good.",
    ]

    # Healthy samples (should NOT be detected)
    healthy_samples = [
        "The cat is running quickly through the yard.",
        "A dog barks loudly at the passing cars.",
        "The bird flies gracefully to the tree.",
        "A man walks fast down the busy street.",
        "The child plays happily with the ball.",
    ]

    # Count detections
    true_positives = sum(1 for text in telegraphic_samples if detector.analyze(text)["is_aphasic"])
    false_positives = sum(1 for text in healthy_samples if detector.analyze(text)["is_aphasic"])

    n_telegraphic = len(telegraphic_samples)

    # Calculate metrics
    snapshot.aphasia_telegraphic_reduction = true_positives / n_telegraphic
    snapshot.aphasia_detection_recall = true_positives / n_telegraphic
    snapshot.aphasia_detection_precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )


def measure_performance_metrics(snapshot: EffectivenessSnapshot) -> None:
    """Measure latency and throughput metrics."""
    from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig

    print("  Measuring performance metrics...")

    def stub_llm_generate(prompt: str, max_tokens: int) -> str:
        time.sleep(max_tokens * 0.000001)
        return f"Generated {max_tokens} tokens"

    def stub_embedding(text: str) -> np.ndarray:
        seed = hash(text) % (2**31)
        return np.random.RandomState(seed).randn(384).astype(np.float32)

    config = NeuroEngineConfig(
        enable_fslgs=False,
        enable_metrics=False,
        initial_moral_threshold=0.5,
    )

    engine = NeuroCognitiveEngine(
        llm_generate_fn=stub_llm_generate,
        embedding_fn=stub_embedding,
        config=config,
    )

    # Collect latency samples
    prompts = [
        "What is the weather today?",
        "Tell me a story about adventure",
        "How do I cook pasta?",
        "Explain quantum physics",
        "What is consciousness?",
    ]

    latencies: list[float] = []
    num_iterations = 50

    for _ in range(num_iterations):
        for prompt in prompts:
            start = time.perf_counter()
            engine.generate(prompt, max_tokens=50)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)

    # Compute percentiles
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_latencies[-1]
        # If k is an integer, return exact value; otherwise interpolate
        if k == f:
            return sorted_latencies[f]
        return sorted_latencies[f] + (k - f) * (sorted_latencies[c] - sorted_latencies[f])

    snapshot.latency_p50_ms = percentile(0.50)
    snapshot.latency_p95_ms = percentile(0.95)
    snapshot.latency_p99_ms = percentile(0.99)


def measure_memory_footprint(snapshot: EffectivenessSnapshot) -> None:
    """Measure PELM memory footprint."""
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

    print("  Measuring memory footprint...")

    gc.collect()
    tracemalloc.start()

    _pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=20_000)

    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    snapshot.memory_footprint_mb = current / (1024 * 1024)


def measure_pelm_throughput(snapshot: EffectivenessSnapshot) -> None:
    """Measure PELM throughput (ops/sec)."""
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

    print("  Measuring PELM throughput...")

    pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=20_000)
    vectors = generate_test_vectors(1000, dim=384)

    # Measure insert throughput
    start = time.perf_counter()
    for i, vec in enumerate(vectors):
        pelm.entangle(vec.tolist(), phase=float(i % 11) / 10.0)
    elapsed = time.perf_counter() - start

    snapshot.pelm_throughput_ops_sec = len(vectors) / elapsed if elapsed > 0 else 0.0


def run_effectiveness_suite(output_dir: Path) -> EffectivenessSnapshot:
    """Run complete effectiveness suite and generate reports."""
    print("=" * 70)
    print("EFFECTIVENESS SUITE")
    print("=" * 70)
    print()

    start_time = time.perf_counter()
    snapshot = EffectivenessSnapshot()
    snapshot.timestamp = datetime.now(timezone.utc).isoformat()

    # Run all measurements
    try:
        measure_toxicity_metrics(snapshot)
    except Exception as e:
        snapshot.errors.append(f"toxicity: {e}")
        print(f"  ERROR in toxicity metrics: {e}")

    try:
        measure_wake_sleep_metrics(snapshot)
    except Exception as e:
        snapshot.errors.append(f"wake_sleep: {e}")
        print(f"  ERROR in wake/sleep metrics: {e}")

    try:
        measure_aphasia_metrics(snapshot)
    except Exception as e:
        snapshot.errors.append(f"aphasia: {e}")
        print(f"  ERROR in aphasia metrics: {e}")

    try:
        measure_performance_metrics(snapshot)
    except Exception as e:
        snapshot.errors.append(f"performance: {e}")
        print(f"  ERROR in performance metrics: {e}")

    try:
        measure_memory_footprint(snapshot)
    except Exception as e:
        snapshot.errors.append(f"memory: {e}")
        print(f"  ERROR in memory footprint: {e}")

    try:
        measure_pelm_throughput(snapshot)
    except Exception as e:
        snapshot.errors.append(f"throughput: {e}")
        print(f"  ERROR in throughput: {e}")

    snapshot.duration_seconds = time.perf_counter() - start_time

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / "effectiveness_snapshot.json"
    with open(json_path, "w") as f:
        json.dump(snapshot.to_dict(), f, indent=2)
    print(f"\n  JSON report: {json_path}")

    # Write Markdown report
    md_path = output_dir / "EFFECTIVENESS_SNAPSHOT.md"
    write_markdown_report(snapshot, md_path)
    print(f"  Markdown report: {md_path}")

    return snapshot


def write_markdown_report(snapshot: EffectivenessSnapshot, path: Path) -> None:
    """Write human-readable Markdown report."""
    content = f"""# Effectiveness Snapshot

**Generated**: {snapshot.timestamp}
**Duration**: {snapshot.duration_seconds:.2f} seconds

## Safety Metrics

| Metric | Value | SLO |
|--------|-------|-----|
| Toxicity Rejection Rate | {snapshot.toxicity_rejection_rate:.2%} | ≥90% |
| False Positive Rate | {snapshot.false_positive_rate:.2%} | — |
| Moral Drift (max) | {snapshot.moral_drift_max:.4f} | ≤0.50 |
| Threshold Convergence | {snapshot.threshold_convergence:.4f} | — |

## Cognitive Metrics

| Metric | Value |
|--------|-------|
| Wake/Sleep Efficiency | {snapshot.wake_to_sleep_efficiency:.2%} |
| Sleep Block Ratio | {snapshot.sleep_block_ratio:.2%} |
| Coherence Gain | {snapshot.coherence_gain:+.4f} |
| Phase Separation | {snapshot.phase_separation:.4f} |

## Aphasia Detection

| Metric | Value | SLO |
|--------|-------|-----|
| Telegraphic Reduction | {snapshot.aphasia_telegraphic_reduction:.2%} | ≥80% |
| Detection Precision | {snapshot.aphasia_detection_precision:.2%} | — |
| Detection Recall | {snapshot.aphasia_detection_recall:.2%} | — |

## Performance Metrics

| Metric | Value | SLO |
|--------|-------|-----|
| Latency P50 | {snapshot.latency_p50_ms:.3f} ms | — |
| Latency P95 | {snapshot.latency_p95_ms:.3f} ms | ≤50 ms |
| Latency P99 | {snapshot.latency_p99_ms:.3f} ms | — |
| PELM Throughput | {snapshot.pelm_throughput_ops_sec:.0f} ops/sec | — |
| Memory Footprint | {snapshot.memory_footprint_mb:.2f} MB | ≤35 MB |

## Errors

"""
    if snapshot.errors:
        for error in snapshot.errors:
            content += f"- {error}\n"
    else:
        content += "No errors during measurement.\n"

    content += """
---

*This report was generated by `scripts/run_effectiveness_suite.py`.*
"""
    with open(path, "w") as f:
        f.write(content)


def validate_slo(snapshot: EffectivenessSnapshot) -> tuple[bool, list[str]]:
    """Validate snapshot against SLO thresholds."""
    failures: list[str] = []

    for metric_name, (op, threshold) in SLO_THRESHOLDS.items():
        value = getattr(snapshot, metric_name, None)
        if value is None:
            failures.append(f"{metric_name}: metric not found")
            continue

        if op == ">=" and value < threshold:
            failures.append(f"{metric_name}: {value:.4f} < {threshold} (SLO: {op}{threshold})")
        elif op == "<=" and value > threshold:
            failures.append(f"{metric_name}: {value:.4f} > {threshold} (SLO: {op}{threshold})")

    return len(failures) == 0, failures


def print_summary(snapshot: EffectivenessSnapshot) -> None:
    """Print summary of effectiveness metrics."""
    print()
    print("=" * 70)
    print("EFFECTIVENESS SUMMARY")
    print("=" * 70)
    print()
    print("Safety:")
    print(f"  toxicity_rejection_rate:   {snapshot.toxicity_rejection_rate:.2%}")
    print(f"  moral_drift_max:           {snapshot.moral_drift_max:.4f}")
    print()
    print("Cognition:")
    print(f"  coherence_gain:            {snapshot.coherence_gain:+.4f}")
    print(f"  wake_to_sleep_efficiency:  {snapshot.wake_to_sleep_efficiency:.2%}")
    print()
    print("Aphasia:")
    print(f"  telegraphic_reduction:     {snapshot.aphasia_telegraphic_reduction:.2%}")
    print()
    print("Performance:")
    print(f"  latency_p50_ms:            {snapshot.latency_p50_ms:.3f}")
    print(f"  latency_p95_ms:            {snapshot.latency_p95_ms:.3f}")
    print(f"  memory_footprint_mb:       {snapshot.memory_footprint_mb:.2f}")
    print(f"  pelm_throughput_ops_sec:   {snapshot.pelm_throughput_ops_sec:.0f}")
    print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run MLSDM effectiveness suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_effectiveness_suite.py
  python scripts/run_effectiveness_suite.py --validate-slo
  python scripts/run_effectiveness_suite.py --output-dir /custom/path
        """,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Output directory for reports (default: reports/)",
    )
    parser.add_argument(
        "--validate-slo",
        action="store_true",
        help="Validate metrics against SLO thresholds and exit with non-zero if failed",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output JSON to stdout and exit (for CI parsing)",
    )
    args = parser.parse_args()

    snapshot = run_effectiveness_suite(args.output_dir)

    if args.json_only:
        print(json.dumps(snapshot.to_dict(), indent=2))
        return 0

    print_summary(snapshot)

    if args.validate_slo:
        passed, failures = validate_slo(snapshot)
        print("=" * 70)
        print("SLO VALIDATION")
        print("=" * 70)
        if passed:
            print("✅ All SLO thresholds passed!")
            return 0
        else:
            print("❌ SLO validation FAILED:")
            for failure in failures:
                print(f"  - {failure}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
