"""Comprehensive tests for mlsdm/router/llm_router.py.

This test module expands coverage to include:
- LLMRouter base class empty providers validation
- LLMRouter get_provider method
- RuleBasedRouter default provider selection (when default is None)
- RuleBasedRouter handling of unhashable metadata values
- ABTestRouter validation errors for missing providers
- ABTestRouter validation for invalid treatment_ratio
- ABTestRouter select_provider full logic paths
"""

from __future__ import annotations

import pytest

from mlsdm.adapters import LocalStubProvider
from mlsdm.router import ABTestRouter, RuleBasedRouter


class TestLLMRouterBaseClass:
    """Tests for LLMRouter base class."""

    def test_empty_providers_raises_value_error(self) -> None:
        """Test that empty providers dict raises ValueError."""
        with pytest.raises(ValueError, match="At least one provider is required"):
            RuleBasedRouter({})

    def test_empty_providers_with_abtestrouter(self) -> None:
        """Test that ABTestRouter also validates empty providers."""
        with pytest.raises(ValueError, match="At least one provider is required"):
            ABTestRouter({}, control="a", treatment="b")


class TestLLMRouterGetProvider:
    """Tests for LLMRouter.get_provider method."""

    def test_get_provider_returns_provider(self) -> None:
        """Test get_provider returns the correct provider."""
        providers = {
            "provider_a": LocalStubProvider(provider_id="a"),
            "provider_b": LocalStubProvider(provider_id="b"),
        }
        router = RuleBasedRouter(providers, default="provider_a")

        provider = router.get_provider("provider_a")
        assert provider.provider_id == "a"

        provider = router.get_provider("provider_b")
        assert provider.provider_id == "b"

    def test_get_provider_raises_key_error(self) -> None:
        """Test get_provider raises KeyError for missing provider."""
        providers = {
            "provider_a": LocalStubProvider(provider_id="a"),
        }
        router = RuleBasedRouter(providers, default="provider_a")

        with pytest.raises(KeyError):
            router.get_provider("nonexistent")


class TestRuleBasedRouterDefaultSelection:
    """Tests for RuleBasedRouter default provider selection."""

    def test_default_none_uses_first_provider(self) -> None:
        """Test that None default uses the first provider."""
        providers = {
            "first_provider": LocalStubProvider(provider_id="first"),
            "second_provider": LocalStubProvider(provider_id="second"),
        }
        # Note: dict order is preserved in Python 3.7+
        router = RuleBasedRouter(providers, default=None)

        assert router.default == "first_provider"

    def test_invalid_default_raises_value_error(self) -> None:
        """Test that invalid default provider raises ValueError."""
        providers = {
            "provider_a": LocalStubProvider(provider_id="a"),
        }

        with pytest.raises(ValueError, match="Default provider 'nonexistent' not found"):
            RuleBasedRouter(providers, default="nonexistent")


class TestRuleBasedRouterMetadataHandling:
    """Tests for RuleBasedRouter handling of various metadata types."""

    def test_unhashable_metadata_values_skipped(self) -> None:
        """Test that unhashable values (lists, dicts) are safely skipped."""
        providers = {
            "default": LocalStubProvider(provider_id="default"),
            "list_matched": LocalStubProvider(provider_id="list_matched"),
        }
        rules = {
            "some_key": "list_matched",
        }
        router = RuleBasedRouter(providers, rules, default="default")

        # Metadata with unhashable list value should not crash
        selected = router.select_provider(
            "test",
            metadata={
                "tags": ["a", "b", "c"],  # list is unhashable
                "config": {"nested": "dict"},  # dict is unhashable
            },
        )
        assert selected == "default"

    def test_none_metadata_values_skipped(self) -> None:
        """Test that None values are safely skipped."""
        providers = {
            "default": LocalStubProvider(provider_id="default"),
        }
        rules = {"some_value": "default"}
        router = RuleBasedRouter(providers, rules, default="default")

        selected = router.select_provider(
            "test",
            metadata={
                "mode": None,
                "user_intent": None,
                "custom_key": None,
            },
        )
        assert selected == "default"

    def test_hashable_custom_metadata_matches_rule(self) -> None:
        """Test that hashable custom metadata values match rules."""
        providers = {
            "default": LocalStubProvider(provider_id="default"),
            "custom_provider": LocalStubProvider(provider_id="custom"),
        }
        rules = {
            "custom_value": "custom_provider",
        }
        router = RuleBasedRouter(providers, rules, default="default")

        # String value should match
        selected = router.select_provider(
            "test",
            metadata={"custom_field": "custom_value"},
        )
        assert selected == "custom_provider"


class TestABTestRouterValidation:
    """Tests for ABTestRouter validation."""

    def test_invalid_control_provider(self) -> None:
        """Test that invalid control provider raises ValueError."""
        providers = {
            "available": LocalStubProvider(provider_id="available"),
        }

        with pytest.raises(ValueError, match="Control provider 'nonexistent' not found"):
            ABTestRouter(
                providers,
                control="nonexistent",
                treatment="available",
            )

    def test_invalid_treatment_provider(self) -> None:
        """Test that invalid treatment provider raises ValueError."""
        providers = {
            "available": LocalStubProvider(provider_id="available"),
        }

        with pytest.raises(ValueError, match="Treatment provider 'nonexistent' not found"):
            ABTestRouter(
                providers,
                control="available",
                treatment="nonexistent",
            )

    def test_treatment_ratio_too_low(self) -> None:
        """Test that treatment_ratio < 0 raises ValueError."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        with pytest.raises(ValueError, match="treatment_ratio must be between 0.0 and 1.0"):
            ABTestRouter(
                providers,
                control="control",
                treatment="treatment",
                treatment_ratio=-0.1,
            )

    def test_treatment_ratio_too_high(self) -> None:
        """Test that treatment_ratio > 1 raises ValueError."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }

        with pytest.raises(ValueError, match="treatment_ratio must be between 0.0 and 1.0"):
            ABTestRouter(
                providers,
                control="control",
                treatment="treatment",
                treatment_ratio=1.5,
            )


class TestABTestRouterSelectProvider:
    """Tests for ABTestRouter.select_provider method."""

    def test_treatment_ratio_zero_always_control(self) -> None:
        """Test that treatment_ratio=0.0 always returns control."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }
        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.0,
        )

        for _ in range(100):
            selected = router.select_provider("test", metadata={})
            assert selected == "control"

    def test_treatment_ratio_one_always_treatment(self) -> None:
        """Test that treatment_ratio=1.0 always returns treatment."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }
        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=1.0,
        )

        for _ in range(100):
            selected = router.select_provider("test", metadata={})
            assert selected == "treatment"

    def test_consistent_hashing_with_user_id(self) -> None:
        """Test consistent hashing returns same result for same user_id."""
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

        # Same user_id should always get same result
        results = [
            router.select_provider("test", metadata={"user_id": "user123"})
            for _ in range(100)
        ]
        assert len(set(results)) == 1  # All results should be the same

    def test_consistent_hashing_different_users(self) -> None:
        """Test consistent hashing gives different results for different users."""
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

        # Generate results for many different users
        results = {
            router.select_provider("test", metadata={"user_id": f"user{i}"})
            for i in range(100)
        }

        # With 50% split and 100 users, we should see both control and treatment
        assert len(results) == 2  # Both control and treatment should appear

    def test_random_sampling_without_user_id(self) -> None:
        """Test random sampling when no user_id provided."""
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

        # Without user_id, should use random sampling
        results = {
            router.select_provider("test", metadata={})
            for _ in range(100)
        }

        # With 50% split and 100 calls, we should likely see both
        # (there's a tiny chance this could fail, but probability is ~2^-100)
        assert len(results) == 2

    def test_random_sampling_with_consistent_hashing_disabled(self) -> None:
        """Test random sampling when consistent hashing is disabled."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }
        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.5,
            use_consistent_hashing=False,  # Disabled
        )

        # Even with user_id, should use random sampling
        results = {
            router.select_provider("test", metadata={"user_id": "user123"})
            for _ in range(100)
        }

        # With 50% split and 100 calls, we should likely see both
        assert len(results) == 2


class TestABTestRouterGetVariant:
    """Tests for ABTestRouter.get_variant method."""

    def test_get_variant_control(self) -> None:
        """Test get_variant returns 'control' for control provider."""
        providers = {
            "ctrl": LocalStubProvider(provider_id="ctrl"),
            "treat": LocalStubProvider(provider_id="treat"),
        }
        router = ABTestRouter(providers, control="ctrl", treatment="treat")

        assert router.get_variant("ctrl") == "control"

    def test_get_variant_treatment(self) -> None:
        """Test get_variant returns 'treatment' for treatment provider."""
        providers = {
            "ctrl": LocalStubProvider(provider_id="ctrl"),
            "treat": LocalStubProvider(provider_id="treat"),
        }
        router = ABTestRouter(providers, control="ctrl", treatment="treat")

        assert router.get_variant("treat") == "treatment"

    def test_get_variant_unknown(self) -> None:
        """Test get_variant returns 'unknown' for unknown provider."""
        providers = {
            "ctrl": LocalStubProvider(provider_id="ctrl"),
            "treat": LocalStubProvider(provider_id="treat"),
        }
        router = ABTestRouter(providers, control="ctrl", treatment="treat")

        assert router.get_variant("other") == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
