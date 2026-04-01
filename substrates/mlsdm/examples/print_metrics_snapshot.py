"""Example script demonstrating metrics collection and export.

This script shows how to:
1. Enable metrics in NeuroCognitiveEngine
2. Generate some requests
3. Export metrics in different formats
"""

import numpy as np

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.observability.exporters import PrometheusPullExporter, StdoutJsonExporter


def stub_llm_generate(prompt: str, max_tokens: int) -> str:
    """Stub LLM function for testing."""
    return f"Generated response for: {prompt[:30]}..."


def stub_embedding(text: str) -> np.ndarray:
    """Stub embedding function for testing."""
    # Simple deterministic embedding based on text length
    return np.random.RandomState(len(text)).randn(384).astype(np.float32)


def main():
    """Demonstrate metrics collection and export."""
    print("=" * 70)
    print("NeuroCognitiveEngine Metrics Snapshot Example")
    print("=" * 70)
    print()

    # Create engine with metrics enabled
    print("Creating NeuroCognitiveEngine with metrics enabled...")
    config = NeuroEngineConfig(
        enable_metrics=True,
        enable_fslgs=False,  # Disable FSLGS for simplicity
    )

    engine = NeuroCognitiveEngine(
        llm_generate_fn=stub_llm_generate,
        embedding_fn=stub_embedding,
        config=config,
    )
    print("✓ Engine created")
    print()

    # Generate some requests
    print("Generating sample requests...")
    print("-" * 70)

    prompts = [
        "What is the meaning of life?",
        "Explain quantum mechanics",
        "Tell me a story",
        "How do I make a cake?",
        "What is consciousness?",
    ]

    for i, prompt in enumerate(prompts, 1):
        result = engine.generate(prompt, max_tokens=100)
        status = "✓" if result["error"] is None else "✗"
        print(f"  {status} Request {i}: {prompt[:40]}")

    print()

    # Get metrics instance
    metrics = engine.get_metrics()
    if metrics is None:
        print("ERROR: Metrics not enabled!")
        return

    print("Metrics collected successfully!")
    print()

    # Export as JSON
    print("JSON Export:")
    print("=" * 70)
    json_exporter = StdoutJsonExporter(metrics)
    json_exporter.print(pretty=True)
    print()

    # Export as Prometheus text
    print("Prometheus Text Export:")
    print("=" * 70)
    prom_exporter = PrometheusPullExporter(metrics)
    print(prom_exporter.render_text())
    print()

    # Show summary statistics
    summary = metrics.get_summary()
    print("Summary Statistics:")
    print("=" * 70)
    print(f"Total Requests: {summary['requests_total']}")
    print(f"Total Rejections: {sum(summary['rejections_total'].values())}")
    print(f"Total Errors: {sum(summary['errors_total'].values())}")
    print()

    print("Latency Statistics:")
    for latency_type, stats in summary["latency_stats"].items():
        if stats["count"] > 0:
            print(f"  {latency_type}:")
            print(f"    Count: {stats['count']}")
            print(f"    Mean: {stats['mean']:.2f}ms")
            print(f"    P50: {stats['p50']:.2f}ms")
            print(f"    P95: {stats['p95']:.2f}ms")
            print(f"    P99: {stats['p99']:.2f}ms")
    print()

    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
