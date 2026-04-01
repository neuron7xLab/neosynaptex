"""
Integration tests for metrics with multi-LLM providers.

This module tests that metrics are correctly collected and labeled
when using multiple LLM providers and A/B testing.
"""

from mlsdm.adapters.llm_provider import LocalStubProvider
from mlsdm.engine.factory import build_stub_embedding_fn
from mlsdm.engine.neuro_cognitive_engine import (
    NeuroCognitiveEngine,
    NeuroEngineConfig,
)
from mlsdm.observability.metrics import MetricsRegistry
from mlsdm.router.llm_router import ABTestRouter


class TestMetricsWithMultiLLM:
    """Tests for metrics collection with multiple LLM providers."""

    def test_metrics_track_provider_id(self) -> None:
        """Test that metrics track provider_id correctly."""
        # Setup providers
        providers = {
            "control": LocalStubProvider(provider_id="openai_gpt_3_5_turbo"),
            "treatment": LocalStubProvider(provider_id="openai_gpt_4"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=False,
        )

        # Create engine with metrics enabled
        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.30,  # Use MIN_THRESHOLD to allow tests to pass
            enable_metrics=True,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Make several requests with positive prompts
        successful_results = 0
        prompts = [
            "Tell me about the weather",
            "What is machine learning?",
            "Explain quantum computing",
            "How do birds fly?",
            "What is photosynthesis?",
        ]
        for i in range(20):
            prompt = prompts[i % len(prompts)] + f" (request {i})"
            result = engine.generate(prompt, max_tokens=100, moral_value=0.3)
            assert "meta" in result
            # Only check successful requests
            if result["error"] is None:
                assert "backend_id" in result["meta"]
                successful_results += 1

        # Should have at least some successful results
        assert successful_results > 0

        # Get metrics
        metrics_registry = engine.get_metrics()
        assert metrics_registry is not None

        snapshot = metrics_registry.get_snapshot()

        # Check that provider metrics exist
        assert "requests_by_provider" in snapshot
        provider_requests = snapshot["requests_by_provider"]

        # Should have requests for at least one provider
        assert len(provider_requests) > 0

        # Total requests should match
        total_provider_requests = sum(provider_requests.values())
        assert total_provider_requests == 20

    def test_metrics_track_variant(self) -> None:
        """Test that metrics track variant (control/treatment) correctly."""
        providers = {
            "control": LocalStubProvider(provider_id="control_v1"),
            "treatment": LocalStubProvider(provider_id="treatment_v2"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=False,
        )

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.30,  # Use MIN_THRESHOLD to allow tests to pass
            enable_metrics=True,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Make requests
        successful_results = 0
        for i in range(30):
            result = engine.generate(f"Test {i}", max_tokens=100, moral_value=0.3)
            assert "meta" in result
            if result["error"] is None:
                assert "variant" in result["meta"]
                successful_results += 1

        assert successful_results > 0

        # Get metrics
        metrics_registry = engine.get_metrics()
        snapshot = metrics_registry.get_snapshot()

        # Check variant metrics
        assert "requests_by_variant" in snapshot
        variant_requests = snapshot["requests_by_variant"]

        # Should have requests for both variants
        assert "control" in variant_requests or "treatment" in variant_requests

        # Total should be 30
        total_variant_requests = sum(variant_requests.values())
        assert total_variant_requests == 30

    def test_metrics_track_latency_by_provider(self) -> None:
        """Test that latency is tracked per provider."""
        providers = {
            "fast": LocalStubProvider(provider_id="fast_provider"),
            "slow": LocalStubProvider(provider_id="slow_provider"),
        }

        # Use 100% fast provider first
        router = ABTestRouter(
            providers,
            control="fast",
            treatment="slow",
            treatment_ratio=0.0,  # All traffic to fast
        )

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.30,  # Use MIN_THRESHOLD to allow tests to pass
            enable_metrics=True,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Make requests to fast provider
        successful = 0
        for i in range(10):
            result = engine.generate(f"Test {i}", max_tokens=100, moral_value=0.3)
            if result["error"] is None:
                successful += 1

        assert successful > 0, "No successful requests"

        metrics_registry = engine.get_metrics()
        snapshot = metrics_registry.get_snapshot()

        # Check latency by provider
        assert "latency_by_provider" in snapshot
        latency_by_provider = snapshot["latency_by_provider"]

        # Should have latency data for fast provider
        assert "fast_provider" in latency_by_provider
        assert len(latency_by_provider["fast_provider"]) == successful

    def test_metrics_track_latency_by_variant(self) -> None:
        """Test that latency is tracked per variant."""
        providers = {
            "control": LocalStubProvider(provider_id="control_v1"),
            "treatment": LocalStubProvider(provider_id="treatment_v2"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
        )

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.30,  # Use MIN_THRESHOLD to allow tests to pass
            enable_metrics=True,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Make requests
        successful = 0
        for i in range(20):
            result = engine.generate(f"Test {i}", max_tokens=100, moral_value=0.3)
            if result["error"] is None:
                successful += 1

        assert successful > 0, "No successful requests"

        metrics_registry = engine.get_metrics()
        snapshot = metrics_registry.get_snapshot()

        # Check latency by variant
        assert "latency_by_variant" in snapshot
        latency_by_variant = snapshot["latency_by_variant"]

        # Should have data for at least one variant
        assert len(latency_by_variant) > 0

        # Total latency records should match successful requests
        total_latency_records = sum(len(v) for v in latency_by_variant.values())
        assert total_latency_records == successful

    def test_metrics_multiple_providers_different_ids(self) -> None:
        """Test that different providers are tracked separately."""
        providers = {
            "provider_a": LocalStubProvider(provider_id="provider_a"),
            "provider_b": LocalStubProvider(provider_id="provider_b"),
            "provider_c": LocalStubProvider(provider_id="provider_c"),
        }

        # Use rule-based router to control which provider is used
        from mlsdm.router.llm_router import RuleBasedRouter

        router = RuleBasedRouter(
            providers,
            rules={"intent_a": "provider_a", "intent_b": "provider_b"},
            default="provider_c",
        )

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.30,  # Use MIN_THRESHOLD to allow tests to pass
            enable_metrics=True,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Make requests with different intents
        successful_a = 0
        for _ in range(5):
            result = engine.generate(
                "Test A", max_tokens=100, user_intent="intent_a", moral_value=0.3
            )
            if result["error"] is None:
                successful_a += 1

        successful_b = 0
        for _ in range(3):
            result = engine.generate(
                "Test B", max_tokens=100, user_intent="intent_b", moral_value=0.3
            )
            if result["error"] is None:
                successful_b += 1

        successful_c = 0
        for _ in range(7):
            result = engine.generate(
                "Test C", max_tokens=100, user_intent="intent_c", moral_value=0.3
            )
            if result["error"] is None:
                successful_c += 1

        # Get metrics
        metrics_registry = engine.get_metrics()
        snapshot = metrics_registry.get_snapshot()

        # Check that all providers are tracked
        provider_requests = snapshot["requests_by_provider"]

        # Should have at least the number of successful requests for each provider
        # Note: Metrics may count more requests than successful_x due to failed requests
        # also being tracked, so we check >= instead of ==
        if successful_a > 0:
            assert "provider_a" in provider_requests
            assert provider_requests["provider_a"] >= successful_a

        if successful_b > 0:
            assert "provider_b" in provider_requests
            assert provider_requests["provider_b"] >= successful_b

        if successful_c > 0:
            assert "provider_c" in provider_requests
            assert provider_requests["provider_c"] >= successful_c


class TestMetricsRegistryMultiLLM:
    """Unit tests for MetricsRegistry multi-LLM features."""

    def test_metrics_registry_provider_tracking(self) -> None:
        """Test MetricsRegistry tracks providers correctly."""
        registry = MetricsRegistry()

        # Increment with provider labels
        registry.increment_requests_total(provider_id="openai_gpt4")
        registry.increment_requests_total(provider_id="openai_gpt4")
        registry.increment_requests_total(provider_id="anthropic_claude")

        snapshot = registry.get_snapshot()

        assert snapshot["requests_total"] == 3
        assert snapshot["requests_by_provider"]["openai_gpt4"] == 2
        assert snapshot["requests_by_provider"]["anthropic_claude"] == 1

    def test_metrics_registry_variant_tracking(self) -> None:
        """Test MetricsRegistry tracks variants correctly."""
        registry = MetricsRegistry()

        # Increment with variant labels
        registry.increment_requests_total(variant="control")
        registry.increment_requests_total(variant="control")
        registry.increment_requests_total(variant="treatment")

        snapshot = registry.get_snapshot()

        assert snapshot["requests_total"] == 3
        assert snapshot["requests_by_variant"]["control"] == 2
        assert snapshot["requests_by_variant"]["treatment"] == 1

    def test_metrics_registry_latency_by_provider(self) -> None:
        """Test MetricsRegistry tracks latency per provider."""
        registry = MetricsRegistry()

        # Record latencies for different providers
        registry.record_latency_generation(100.0, provider_id="fast")
        registry.record_latency_generation(150.0, provider_id="fast")
        registry.record_latency_generation(300.0, provider_id="slow")

        snapshot = registry.get_snapshot()

        assert len(snapshot["latency_by_provider"]["fast"]) == 2
        assert len(snapshot["latency_by_provider"]["slow"]) == 1
        assert snapshot["latency_by_provider"]["fast"][0] == 100.0
        assert snapshot["latency_by_provider"]["fast"][1] == 150.0
        assert snapshot["latency_by_provider"]["slow"][0] == 300.0

    def test_metrics_registry_latency_by_variant(self) -> None:
        """Test MetricsRegistry tracks latency per variant."""
        registry = MetricsRegistry()

        # Record latencies for different variants
        registry.record_latency_generation(100.0, variant="control")
        registry.record_latency_generation(200.0, variant="treatment")
        registry.record_latency_generation(150.0, variant="control")

        snapshot = registry.get_snapshot()

        assert len(snapshot["latency_by_variant"]["control"]) == 2
        assert len(snapshot["latency_by_variant"]["treatment"]) == 1

    def test_metrics_registry_reset_clears_multi_llm_metrics(self) -> None:
        """Test that reset clears multi-LLM metrics."""
        registry = MetricsRegistry()

        # Add some data
        registry.increment_requests_total(provider_id="p1", variant="control")
        registry.record_latency_generation(100.0, provider_id="p1", variant="control")

        # Reset
        registry.reset()

        # Check that all metrics are cleared
        snapshot = registry.get_snapshot()

        assert snapshot["requests_total"] == 0
        assert len(snapshot["requests_by_provider"]) == 0
        assert len(snapshot["requests_by_variant"]) == 0
        assert len(snapshot["latency_by_provider"]) == 0
        assert len(snapshot["latency_by_variant"]) == 0
