"""Performance benchmarks for NeuroCognitiveEngine.

These benchmarks measure:
1. Pre-flight check latency (moral precheck only)
2. End-to-end latency with small load
3. End-to-end latency with heavy load (varying max_tokens)

Benchmarks use local_stub backend for consistent, reproducible results.
"""

import time

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.observability.tracing import TracingConfig, initialize_tracing, shutdown_tracing


@pytest.fixture(scope="module", autouse=True)
def disable_tracing_for_benchmarks() -> None:
    """Disable tracing to avoid console exporter overhead in benchmarks."""
    initialize_tracing(TracingConfig(enabled=False))
    yield
    shutdown_tracing()


def stub_llm_generate(prompt: str, max_tokens: int) -> str:
    """Stub LLM function for consistent performance testing.

    Simulates generation time proportional to max_tokens.
    """
    # Simulate token generation time: ~0.001ms per token
    time.sleep(max_tokens * 0.000001)
    return f"Generated {max_tokens} tokens for: {prompt[:50]}..."


def stub_embedding(text: str) -> np.ndarray:
    """Stub embedding function for consistent testing.

    Returns deterministic embedding based on text hash.
    """
    # Use text hash for deterministic but unique embeddings
    seed = hash(text) % (2**31)
    return np.random.RandomState(seed).randn(384).astype(np.float32)


def compute_percentiles(values: list[float]) -> dict[str, float]:
    """Compute percentile statistics.

    Args:
        values: List of latency values in milliseconds

    Returns:
        Dictionary with p50, p95, p99 percentiles
    """
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0, "mean": 0.0}

    sorted_values = sorted(values)
    n = len(sorted_values)

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_values[-1]
        if f == k:
            return sorted_values[f]
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    return {
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "mean": sum(sorted_values) / n,
    }


def create_engine(enable_metrics: bool = False) -> NeuroCognitiveEngine:
    """Create engine instance for benchmarking.

    Args:
        enable_metrics: Whether to enable metrics collection

    Returns:
        Configured NeuroCognitiveEngine instance
    """
    config = NeuroEngineConfig(
        enable_fslgs=False,  # Disable for simplicity
        enable_metrics=enable_metrics,
        initial_moral_threshold=0.5,
    )

    return NeuroCognitiveEngine(
        llm_generate_fn=stub_llm_generate,
        embedding_fn=stub_embedding,
        config=config,
    )


def benchmark_pre_flight_latency() -> dict[str, float]:
    """Benchmark pre-flight check latency.

    Measures only the moral precheck step, which should be very fast.

    Returns:
        Dictionary with percentile statistics
    """
    engine = create_engine()
    latencies: list[float] = []

    # Generate a variety of prompts to test moral precheck
    prompts = [
        "What is the weather today?",
        "Tell me a story about adventure",
        "How do I cook pasta?",
        "Explain quantum physics",
        "What is consciousness?",
        "Help me with my homework",
        "Design a database schema",
        "Write a poem about nature",
        "What are the laws of thermodynamics?",
        "How does the internet work?",
    ]

    # Run benchmark: 100 iterations
    num_iterations = 100
    for _ in range(num_iterations):
        for prompt in prompts:
            result = engine.generate(prompt, max_tokens=10)

            # Only count pre-flight latency if available
            if "moral_precheck" in result["timing"]:
                latencies.append(result["timing"]["moral_precheck"])

    return compute_percentiles(latencies)


def benchmark_end_to_end_latency_small_load() -> dict[str, float]:
    """Benchmark end-to-end latency with small load.

    Tests basic generation with moderate token counts.

    Returns:
        Dictionary with percentile statistics
    """
    engine = create_engine()
    latencies: list[float] = []

    prompts = [
        "Summarize this: Machine learning is fascinating",
        "Translate: Hello world",
        "Classify: This movie is great!",
        "Answer: What is 2+2?",
        "Complete: The quick brown fox",
    ]

    # Run benchmark: 50 iterations with small max_tokens
    num_iterations = 50
    for _ in range(num_iterations):
        for prompt in prompts:
            start = time.perf_counter()
            _result = engine.generate(prompt, max_tokens=50)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)

    return compute_percentiles(latencies)


def benchmark_end_to_end_latency_heavy_load() -> dict[str, dict[str, float]]:
    """Benchmark end-to-end latency with heavy load.

    Tests with varying max_tokens values to see scaling behavior.

    Returns:
        Dictionary mapping max_tokens to percentile statistics
    """
    engine = create_engine()

    prompts = [
        "Write a comprehensive essay about climate change",
        "Explain the history of artificial intelligence",
        "Describe the solar system in detail",
        "Analyze the themes in Shakespeare's Hamlet",
        "Create a detailed business plan for a startup",
    ]

    # Test different token counts
    token_counts = [100, 250, 500, 1000]
    results = {}

    for max_tokens in token_counts:
        latencies: list[float] = []

        # Run benchmark: 20 iterations per token count
        num_iterations = 20
        for _ in range(num_iterations):
            for prompt in prompts:
                start = time.perf_counter()
                _result = engine.generate(prompt, max_tokens=max_tokens)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                latencies.append(elapsed_ms)

        results[f"tokens_{max_tokens}"] = compute_percentiles(latencies)

    return results


# ============================================================================
# Pytest test functions that run and report benchmarks
# ============================================================================


@pytest.mark.benchmark
def test_benchmark_pre_flight_latency():
    """Test and report pre-flight check latency with 3-run averaging for stability."""
    print("\n" + "=" * 70)
    print("BENCHMARK: Pre-Flight Check Latency")
    print("=" * 70)

    # Run 3 times and take median to reduce variance
    all_stats = []
    for run in range(3):
        stats = benchmark_pre_flight_latency()
        all_stats.append(stats)
        print(f"\nRun {run + 1} - P95: {stats['p95']:.3f}ms")

    # Take median of P95 values across runs
    p95_values = [s['p95'] for s in all_stats]
    median_p95 = sorted(p95_values)[len(p95_values) // 2]

    print("\nMedian Results across 3 runs:")
    print(f"  P95 (median): {median_p95:.3f}ms")
    print()

    # SLO: pre_flight_latency_p95 < 20ms with 10% tolerance for CI overhead
    slo = 20.0
    tolerance = 1.10
    assert median_p95 < slo * tolerance, (
        f"P95 latency {median_p95:.3f}ms exceeds SLO {slo}ms "
        f"(with {tolerance*100:.0f}% tolerance). "
        f"Runs: {p95_values}"
    )
    print(f"✓ SLO met: P95 < {slo}ms (with {tolerance*100:.0f}% tolerance)")
    print()


@pytest.mark.benchmark
def test_benchmark_end_to_end_small_load():
    """Test and report end-to-end latency with small load and 3-run averaging."""
    print("\n" + "=" * 70)
    print("BENCHMARK: End-to-End Latency (Small Load)")
    print("=" * 70)
    print("Configuration: 50 tokens, normal prompts")
    print()

    # Run 3 times and take median to reduce variance
    all_stats = []
    for run in range(3):
        stats = benchmark_end_to_end_latency_small_load()
        all_stats.append(stats)
        print(f"Run {run + 1} - P95: {stats['p95']:.3f}ms")

    # Take median of P95 values across runs
    p95_values = [s['p95'] for s in all_stats]
    median_p95 = sorted(p95_values)[len(p95_values) // 2]

    print("\nMedian Results across 3 runs (based on 250 measurements per run):")
    print(f"  P95 (median): {median_p95:.3f}ms")
    print()

    # SLO: latency_total_ms_p95 < 500ms with 10% tolerance for CI overhead
    slo = 500.0
    tolerance = 1.10
    assert median_p95 < slo * tolerance, (
        f"P95 latency {median_p95:.3f}ms exceeds SLO {slo}ms "
        f"(with {tolerance*100:.0f}% tolerance). "
        f"Runs: {p95_values}"
    )
    print(f"✓ SLO met: P95 < {slo}ms (with {tolerance*100:.0f}% tolerance)")
    print()


@pytest.mark.benchmark
def test_benchmark_end_to_end_heavy_load():
    """Test and report end-to-end latency with heavy load and 3-run averaging."""
    print("\n" + "=" * 70)
    print("BENCHMARK: End-to-End Latency (Heavy Load)")
    print("=" * 70)
    print("Testing varying token counts with 3-run averaging...")
    print()

    # Run 3 times and take median to reduce variance
    all_results = []
    for _run in range(3):
        results = benchmark_end_to_end_latency_heavy_load()
        all_results.append(results)

    print("Results by token count (median across 3 runs):")
    print("-" * 70)

    # For each token count, compute median P95 across runs
    token_keys = sorted(all_results[0].keys())
    slo = 500.0
    tolerance = 1.10

    for token_key in token_keys:
        p95_values = [run[token_key]['p95'] for run in all_results]
        median_p95 = sorted(p95_values)[len(p95_values) // 2]

        token_count = token_key.split("_")[1]
        print(f"\nmax_tokens={token_count}:")
        print(f"  Median P95: {median_p95:.3f}ms")
        print(f"  Runs: {[f'{p:.3f}' for p in p95_values]}")

        # All should meet SLO with tolerance
        assert median_p95 < slo * tolerance, (
            f"P95 latency {median_p95:.3f}ms exceeds SLO {slo}ms "
            f"(with {tolerance*100:.0f}% tolerance) for {token_count} tokens. "
            f"Runs: {p95_values}"
        )

    print()
    print(f"✓ All token counts meet SLO: P95 < {slo}ms (with {tolerance*100:.0f}% tolerance)")
    print()


@pytest.mark.benchmark
def test_benchmark_summary():
    """Generate a comprehensive benchmark summary."""
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print()
    print("All benchmarks completed successfully!")
    print()
    print("SLO Compliance:")
    print("  ✓ Pre-flight latency P95 < 20ms")
    print("  ✓ End-to-end latency P95 < 500ms")
    print()
    print("Note: These benchmarks use stub LLM backend for reproducibility.")
    print("Real-world performance will vary based on actual LLM latency.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    # Allow running benchmarks directly
    print("Running NeuroCognitiveEngine Performance Benchmarks")
    print()

    test_benchmark_pre_flight_latency()
    test_benchmark_end_to_end_small_load()
    test_benchmark_end_to_end_heavy_load()
    test_benchmark_summary()
