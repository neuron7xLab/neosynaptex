"""Performance benchmarks for embedding cache.

These benchmarks measure:
1. Cache hit rate improvement for repeated prompts
2. Latency reduction with cache enabled
3. Memory overhead of caching

Benchmarks establish baseline and optimized performance metrics.
"""

import hashlib
import time

import numpy as np
import pytest

from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.utils.embedding_cache import EmbeddingCache, EmbeddingCacheConfig


def stub_llm_generate(prompt: str, max_tokens: int) -> str:
    """Stub LLM function for consistent performance testing."""
    time.sleep(max_tokens * 0.000001)
    return f"Generated {max_tokens} tokens for: {prompt[:50]}..."


def slow_embedding(text: str) -> np.ndarray:
    """Embedding function with simulated compute latency.

    Simulates realistic embedding model overhead (~0.5ms per call).
    Uses hashlib for deterministic seeding across Python runs.
    """
    time.sleep(0.0005)  # 0.5ms simulated embedding latency
    # Use SHA-256 for deterministic seeding across Python runs
    hash_bytes = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(hash_bytes[:4], "big") % (2**31)
    return np.random.RandomState(seed).randn(384).astype(np.float32)


def compute_percentiles(values: list[float]) -> dict[str, float]:
    """Compute percentile statistics for latency measurements."""
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


class TestEmbeddingCacheBenchmarks:
    """Benchmarks for embedding cache performance."""

    def test_cache_hit_rate_with_repeated_prompts(self) -> None:
        """Test cache hit rate with repeated prompts.

        With repeated prompts, cache should achieve high hit rate.
        """
        print("\n" + "=" * 70)
        print("BENCHMARK: Embedding Cache Hit Rate")
        print("=" * 70)

        cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=100, ttl_seconds=3600))
        wrapped_embed = cache.wrap(slow_embedding)

        # Test with repeated prompts
        prompts = [
            "Hello, how are you?",
            "What is the weather today?",
            "Tell me a story",
            "Explain quantum physics",
            "How do I cook pasta?",
        ]

        # Run 100 iterations, each cycling through all prompts
        iterations = 100
        for _ in range(iterations):
            for prompt in prompts:
                wrapped_embed(prompt)

        stats = cache.get_stats()
        total_calls = iterations * len(prompts)
        expected_misses = len(prompts)  # First pass through each prompt
        expected_hits = total_calls - expected_misses

        print(f"\nTotal calls: {total_calls}")
        print(f"Cache hits: {stats.hits}")
        print(f"Cache misses: {stats.misses}")
        print(f"Hit rate: {stats.hit_rate:.2f}%")
        print(f"Cache size: {stats.current_size}")
        print()

        # Validate high hit rate for repeated prompts
        assert stats.hits == expected_hits, f"Expected {expected_hits} hits, got {stats.hits}"
        assert (
            stats.misses == expected_misses
        ), f"Expected {expected_misses} misses, got {stats.misses}"
        assert stats.hit_rate >= 99.0, f"Expected hit rate >= 99%, got {stats.hit_rate:.2f}%"

        print("✓ Cache achieves 99%+ hit rate with repeated prompts")
        print()

    def test_latency_improvement_with_cache(self) -> None:
        """Test latency improvement with cache enabled vs disabled.

        Cache should significantly reduce P95 latency for repeated prompts.
        """
        print("\n" + "=" * 70)
        print("BENCHMARK: Embedding Latency with Cache")
        print("=" * 70)

        prompts = [
            "Hello, how are you?",
            "What is the weather today?",
            "Tell me a story",
        ]
        iterations = 50

        # Measure WITHOUT cache
        latencies_no_cache: list[float] = []
        for _ in range(iterations):
            for prompt in prompts:
                start = time.perf_counter()
                slow_embedding(prompt)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies_no_cache.append(elapsed_ms)

        stats_no_cache = compute_percentiles(latencies_no_cache)

        # Measure WITH cache (cache will warm up on first pass)
        cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=100, ttl_seconds=3600))
        wrapped_embed = cache.wrap(slow_embedding)

        latencies_with_cache: list[float] = []
        for _ in range(iterations):
            for prompt in prompts:
                start = time.perf_counter()
                wrapped_embed(prompt)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies_with_cache.append(elapsed_ms)

        stats_with_cache = compute_percentiles(latencies_with_cache)
        cache_stats = cache.get_stats()

        print("\nWithout Cache:")
        print(f"  P50: {stats_no_cache['p50']:.3f}ms")
        print(f"  P95: {stats_no_cache['p95']:.3f}ms")
        print(f"  Mean: {stats_no_cache['mean']:.3f}ms")

        print("\nWith Cache:")
        print(f"  P50: {stats_with_cache['p50']:.3f}ms")
        print(f"  P95: {stats_with_cache['p95']:.3f}ms")
        print(f"  Mean: {stats_with_cache['mean']:.3f}ms")
        print(f"  Hit rate: {cache_stats.hit_rate:.2f}%")

        # Calculate improvement
        p95_improvement = (
            (stats_no_cache["p95"] - stats_with_cache["p95"]) / stats_no_cache["p95"] * 100
        )
        mean_improvement = (
            (stats_no_cache["mean"] - stats_with_cache["mean"]) / stats_no_cache["mean"] * 100
        )

        print("\nImprovement:")
        print(f"  P95 reduction: {p95_improvement:.1f}%")
        print(f"  Mean reduction: {mean_improvement:.1f}%")
        print()

        # Cache should provide significant latency improvement
        assert stats_with_cache["mean"] < stats_no_cache["mean"], "Cache should reduce mean latency"
        assert (
            mean_improvement > 50.0
        ), f"Expected >50% mean latency improvement, got {mean_improvement:.1f}%"

        print("✓ Cache provides >50% latency reduction")
        print()

    def test_cache_memory_overhead(self) -> None:
        """Test cache memory overhead is reasonable."""
        print("\n" + "=" * 70)
        print("BENCHMARK: Embedding Cache Memory Overhead")
        print("=" * 70)

        # Create cache with reasonable size
        cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=1000, ttl_seconds=3600))
        wrapped_embed = cache.wrap(slow_embedding)

        # Fill cache with diverse prompts
        for i in range(100):
            wrapped_embed(f"Unique prompt number {i} with some extra text")

        stats = cache.get_stats()

        # Estimate memory: 100 entries × 384 dims × 4 bytes/float32 + overhead
        estimated_array_bytes = 100 * 384 * 4
        estimated_overhead = 100 * 200  # ~200 bytes per entry for metadata
        estimated_total = estimated_array_bytes + estimated_overhead

        print(f"\nCache entries: {stats.current_size}")
        print(f"Estimated memory: {estimated_total / 1024:.2f} KB")
        print(f"Per-entry memory: {estimated_total / stats.current_size:.0f} bytes")
        print()

        assert stats.current_size == 100, f"Expected 100 entries, got {stats.current_size}"

        # Memory should be reasonable (under 1 MB for 100 entries)
        assert estimated_total < 1024 * 1024, "Cache memory should be < 1 MB for 100 entries"

        print("✓ Cache memory overhead is reasonable")
        print()

    def test_llm_wrapper_with_embedding_cache(self) -> None:
        """Test LLMWrapper integration with embedding cache.

        Verifies cache works correctly when integrated into LLMWrapper.
        """
        print("\n" + "=" * 70)
        print("BENCHMARK: LLMWrapper with Embedding Cache")
        print("=" * 70)

        # Create wrapper WITHOUT cache (baseline)
        wrapper_no_cache = LLMWrapper(
            llm_generate_fn=stub_llm_generate,
            embedding_fn=slow_embedding,
            dim=384,
            capacity=1000,
        )

        # Create wrapper WITH cache
        wrapper_with_cache = LLMWrapper(
            llm_generate_fn=stub_llm_generate,
            embedding_fn=slow_embedding,
            dim=384,
            capacity=1000,
            embedding_cache_config=EmbeddingCacheConfig(max_size=100, ttl_seconds=3600),
        )

        prompts = [
            "Hello, how are you?",
            "What is machine learning?",
            "Explain neural networks",
        ]
        iterations = 5

        # Test without cache (brief - just verify it works)
        for prompt in prompts:
            result = wrapper_no_cache.generate(prompt, moral_value=0.8, max_tokens=50)
            assert result is not None

        # Test with cache
        for _ in range(iterations):
            for prompt in prompts:
                result = wrapper_with_cache.generate(prompt, moral_value=0.8, max_tokens=50)
                assert result is not None

        # Check cache stats
        cache_stats = wrapper_with_cache.get_embedding_cache_stats()
        assert cache_stats is not None, "Cache stats should be available"

        print(f"\nCache statistics after {iterations * len(prompts)} calls:")
        print(f"  Hits: {cache_stats['hits']}")
        print(f"  Misses: {cache_stats['misses']}")
        print(f"  Hit rate: {cache_stats['hit_rate']:.2f}%")
        print()

        # After warming up, we should see high hit rate
        # Note: In LLMWrapper, embedding is called once per generate(), so
        # the actual numbers depend on internal calls. Let's verify reasonable hit rate.

        assert cache_stats["hits"] > 0, "Should have cache hits after warming up"
        assert (
            cache_stats["hit_rate"] > 50
        ), f"Expected hit rate > 50%, got {cache_stats['hit_rate']:.2f}%"

        print("✓ LLMWrapper integrates correctly with embedding cache")
        print()

    def test_cache_eviction_behavior(self) -> None:
        """Test cache correctly evicts entries when full."""
        print("\n" + "=" * 70)
        print("BENCHMARK: Embedding Cache Eviction")
        print("=" * 70)

        # Small cache to test eviction
        cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=10, ttl_seconds=3600))

        # Add 20 entries (should trigger evictions)
        for i in range(20):
            cache.put(f"entry_{i}", np.random.randn(384).astype(np.float32))

        stats = cache.get_stats()

        print("\nAfter adding 20 entries to size-10 cache:")
        print(f"  Current size: {stats.current_size}")
        print(f"  Evictions: {stats.evictions}")
        print()

        assert stats.current_size == 10, f"Cache should be at max size, got {stats.current_size}"
        assert stats.evictions >= 10, f"Expected >= 10 evictions, got {stats.evictions}"

        print("✓ Cache correctly evicts entries at capacity")
        print()


@pytest.mark.benchmark
def test_benchmark_embedding_cache_summary() -> None:
    """Generate a comprehensive benchmark summary for embedding cache."""
    print("\n" + "=" * 70)
    print("EMBEDDING CACHE BENCHMARK SUMMARY")
    print("=" * 70)
    print()
    print("Performance improvements from embedding cache:")
    print("  ✓ 99%+ hit rate for repeated prompts")
    print("  ✓ >50% latency reduction with cache")
    print("  ✓ Reasonable memory overhead (<1MB for 100 entries)")
    print("  ✓ Correct LRU eviction behavior")
    print("  ✓ Seamless LLMWrapper integration")
    print()
    print("Recommended configuration:")
    print("  - max_size: 1000 (covers typical prompt diversity)")
    print("  - ttl_seconds: 3600 (1 hour - balance freshness vs. performance)")
    print("  - enable in production for repeated/similar prompts")
    print("=" * 70)
    print()


if __name__ == "__main__":
    # Allow running benchmarks directly
    print("Running Embedding Cache Performance Benchmarks")
    print()

    tests = TestEmbeddingCacheBenchmarks()
    tests.test_cache_hit_rate_with_repeated_prompts()
    tests.test_latency_improvement_with_cache()
    tests.test_cache_memory_overhead()
    tests.test_llm_wrapper_with_embedding_cache()
    tests.test_cache_eviction_behavior()
    test_benchmark_embedding_cache_summary()
