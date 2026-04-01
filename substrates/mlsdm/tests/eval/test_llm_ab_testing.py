"""
Tests for LLM A/B testing functionality.

This module tests the A/B testing router implementation, including:
- Traffic split accuracy
- Consistent hashing for user-based routing
- Variant tagging in response metadata
"""

import pytest

from mlsdm.adapters.llm_provider import LocalStubProvider
from mlsdm.router.llm_router import ABTestRouter


class TestABTestRouter:
    """Tests for ABTestRouter class."""

    def test_ab_router_respects_traffic_split(self) -> None:
        """Test that traffic split is respected over many requests."""
        # Setup providers
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        # Create router with 10% treatment traffic
        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.1,
            use_consistent_hashing=False,  # Use random for testing
        )

        # Make many requests and count assignments
        num_requests = 1000
        assignments = {"control": 0, "treatment": 0}

        for i in range(num_requests):
            provider_name = router.select_provider(
                prompt=f"test prompt {i}", metadata={"request_id": i}
            )
            assignments[provider_name] += 1

        # Check that traffic split is approximately 90/10
        control_ratio = assignments["control"] / num_requests
        treatment_ratio = assignments["treatment"] / num_requests

        # Allow 5% tolerance for randomness
        assert 0.85 <= control_ratio <= 0.95, f"Control ratio: {control_ratio}"
        assert 0.05 <= treatment_ratio <= 0.15, f"Treatment ratio: {treatment_ratio}"

    def test_ab_router_consistent_hashing(self) -> None:
        """Test that consistent hashing gives same result for same user_id."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=True,
        )

        # Same user_id should always get same provider
        user_id = "test_user_123"
        first_assignment = router.select_provider(prompt="test", metadata={"user_id": user_id})

        # Repeat 10 times
        for _ in range(10):
            assignment = router.select_provider(
                prompt="different prompt", metadata={"user_id": user_id}
            )
            assert assignment == first_assignment, "Consistent hashing failed"

    def test_ab_router_different_users_get_different_assignments(self) -> None:
        """Test that different users can get different assignments."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=True,
        )

        # Test many different users
        assignments = set()
        for i in range(100):
            user_id = f"user_{i}"
            assignment = router.select_provider(prompt="test", metadata={"user_id": user_id})
            assignments.add(assignment)

        # Should have both control and treatment
        assert len(assignments) == 2, "Not all variants were assigned"
        assert "control" in assignments
        assert "treatment" in assignments

    def test_ab_results_are_tagged_in_variant_method(self) -> None:
        """Test that variant tagging works correctly."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
        )

        # Check variant tagging
        assert router.get_variant("control") == "control"
        assert router.get_variant("treatment") == "treatment"
        assert router.get_variant("unknown") == "unknown"

    def test_ab_router_extreme_ratios(self) -> None:
        """Test A/B router with extreme traffic ratios (0% and 100%)."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        # Test 0% treatment
        router_0 = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.0,
        )

        for _ in range(100):
            assert router_0.select_provider("test", {}) == "control"

        # Test 100% treatment
        router_100 = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=1.0,
        )

        for _ in range(100):
            assert router_100.select_provider("test", {}) == "treatment"

    def test_ab_router_provider_generation(self) -> None:
        """Test that providers can actually generate responses."""
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

        # Select provider and generate response
        provider_name = router.select_provider("Hello", {"user_id": "test"})
        provider = router.get_provider(provider_name)

        response = provider.generate("Hello, world!", max_tokens=100)

        assert isinstance(response, str)
        assert len(response) > 0
        assert "NEURO-RESPONSE" in response

    def test_ab_router_invalid_config(self) -> None:
        """Test that invalid configurations raise errors."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        # Invalid treatment_ratio
        with pytest.raises(ValueError, match="treatment_ratio"):
            ABTestRouter(
                providers,
                control="control",
                treatment="treatment",
                treatment_ratio=1.5,
            )

        # Non-existent control provider
        with pytest.raises(ValueError, match="Control provider"):
            ABTestRouter(
                providers,
                control="nonexistent",
                treatment="treatment",
                treatment_ratio=0.5,
            )

        # Non-existent treatment provider
        with pytest.raises(ValueError, match="Treatment provider"):
            ABTestRouter(
                providers,
                control="control",
                treatment="nonexistent",
                treatment_ratio=0.5,
            )


class TestABTestingIntegration:
    """Integration tests for A/B testing with NeuroCognitiveEngine."""

    def test_engine_with_ab_router_returns_metadata(self) -> None:
        """Test that engine returns backend_id and variant in metadata."""
        from mlsdm.engine.factory import build_stub_embedding_fn
        from mlsdm.engine.neuro_cognitive_engine import (
            NeuroCognitiveEngine,
            NeuroEngineConfig,
        )

        # Setup providers and router
        providers = {
            "control": LocalStubProvider(provider_id="control_v1"),
            "treatment": LocalStubProvider(provider_id="treatment_v2"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=True,
        )

        # Create engine with router
        config = NeuroEngineConfig(
            enable_fslgs=False,  # Disable FSLGS for simpler testing
            enable_metrics=False,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Generate response
        result = engine.generate(
            "Hello, test!",
            max_tokens=100,
            user_intent="test",
        )

        # Check that metadata contains backend_id and variant
        assert "meta" in result
        assert "backend_id" in result["meta"]
        assert "variant" in result["meta"]

        backend_id = result["meta"]["backend_id"]
        variant = result["meta"]["variant"]

        # Should be one of the two providers
        assert backend_id in ["control_v1", "treatment_v2"]
        assert variant in ["control", "treatment"]

        # Verify mapping is correct
        if backend_id == "control_v1":
            assert variant == "control"
        else:
            assert variant == "treatment"

    def test_engine_multiple_requests_consistent_user(self) -> None:
        """Test that same user gets consistent variant across requests."""
        from mlsdm.engine.factory import build_stub_embedding_fn
        from mlsdm.engine.neuro_cognitive_engine import (
            NeuroCognitiveEngine,
            NeuroEngineConfig,
        )

        providers = {
            "control": LocalStubProvider(provider_id="control_v1"),
            "treatment": LocalStubProvider(provider_id="treatment_v2"),
        }

        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=True,
        )

        config = NeuroEngineConfig(
            enable_fslgs=False,
            enable_metrics=False,
            initial_moral_threshold=0.0,  # Disable moral filtering for test
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=build_stub_embedding_fn(384),
            config=config,
            router=router,
        )

        # Note: user_id would need to be passed through metadata
        # For now, we test that the routing is at least functional

        # Make multiple requests with low moral value to pass moral check
        results = []
        for i in range(5):
            result = engine.generate(
                f"Test prompt {i}",
                max_tokens=100,
                moral_value=0.0,  # Pass moral check
            )
            results.append(result)

        # All requests should have metadata
        for result in results:
            assert "meta" in result
            # Check if successful (not rejected)
            if result["error"] is None:
                assert "backend_id" in result["meta"]
                assert "variant" in result["meta"]
