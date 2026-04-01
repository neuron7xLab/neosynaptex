"""
Unit tests for LLM Router functionality.

Tests cover:
1. RuleBasedRouter with mode-based routing ("cheap", "safe", "deep")
2. Fallback behavior when provider unavailable
3. RouterError exception
4. Priority of routing rules
"""

import pytest

from mlsdm.adapters import LocalStubProvider
from mlsdm.router import ABTestRouter, RouterError, RuleBasedRouter


class TestRuleBasedRouterModeRouting:
    """Tests for mode-based routing in RuleBasedRouter."""

    def test_mode_cheap(self) -> None:
        """Test routing for 'cheap' mode."""
        providers = {
            "expensive_llm": LocalStubProvider(provider_id="expensive"),
            "cheap_llm": LocalStubProvider(provider_id="cheap"),
        }
        rules = {
            "cheap": "cheap_llm",
            "deep": "expensive_llm",
        }
        router = RuleBasedRouter(providers, rules, default="cheap_llm")

        selected = router.select_provider("test", metadata={"mode": "cheap"})
        assert selected == "cheap_llm"

    def test_mode_deep(self) -> None:
        """Test routing for 'deep' mode."""
        providers = {
            "gpt4": LocalStubProvider(provider_id="gpt4"),
            "local": LocalStubProvider(provider_id="local"),
        }
        rules = {
            "deep": "gpt4",
            "safe": "local",
        }
        router = RuleBasedRouter(providers, rules, default="local")

        selected = router.select_provider("test", metadata={"mode": "deep"})
        assert selected == "gpt4"

    def test_mode_safe(self) -> None:
        """Test routing for 'safe' mode."""
        providers = {
            "risky": LocalStubProvider(provider_id="risky"),
            "safe": LocalStubProvider(provider_id="safe"),
        }
        rules = {
            "safe": "safe",
            "deep": "risky",
        }
        router = RuleBasedRouter(providers, rules, default="risky")

        selected = router.select_provider("test", metadata={"mode": "safe"})
        assert selected == "safe"

    def test_mode_takes_priority_over_intent(self) -> None:
        """Test that mode takes priority over user_intent."""
        providers = {
            "a": LocalStubProvider(provider_id="a"),
            "b": LocalStubProvider(provider_id="b"),
            "c": LocalStubProvider(provider_id="c"),
        }
        rules = {
            "cheap": "a",
            "conversational": "b",
        }
        router = RuleBasedRouter(providers, rules, default="c")

        # Mode should take priority
        selected = router.select_provider(
            "test",
            metadata={"mode": "cheap", "user_intent": "conversational"},
        )
        assert selected == "a"


class TestRuleBasedRouterFallback:
    """Tests for fallback behavior in RuleBasedRouter."""

    def test_fallback_to_default_on_missing_provider(self) -> None:
        """Test fallback to default when rule points to missing provider."""
        providers = {
            "available": LocalStubProvider(provider_id="available"),
        }
        # Rule points to non-existent provider
        rules = {
            "deep": "missing_provider",
        }
        router = RuleBasedRouter(
            providers,
            rules,
            default="available",
            fallback_on_error=True,
        )

        # Should fallback to default
        selected = router.select_provider("test", metadata={"mode": "deep"})
        assert selected == "available"

    def test_no_fallback_raises_error(self) -> None:
        """Test that RouterError is raised when fallback is disabled."""
        providers = {
            "available": LocalStubProvider(provider_id="available"),
        }
        rules = {
            "deep": "missing_provider",
        }
        router = RuleBasedRouter(
            providers,
            rules,
            default="available",
            fallback_on_error=False,
        )

        with pytest.raises(RouterError) as exc_info:
            router.select_provider("test", metadata={"mode": "deep"})

        assert exc_info.value.requested_provider == "missing_provider"
        assert "available" in exc_info.value.available_providers

    def test_default_fallback_when_no_rule_matches(self) -> None:
        """Test fallback to default when no rule matches."""
        providers = {
            "default_provider": LocalStubProvider(provider_id="default"),
            "other": LocalStubProvider(provider_id="other"),
        }
        rules = {"deep": "other"}
        router = RuleBasedRouter(providers, rules, default="default_provider")

        # No matching rule, should use default
        selected = router.select_provider("test", metadata={"foo": "bar"})
        assert selected == "default_provider"


class TestRouterError:
    """Tests for RouterError exception."""

    def test_basic_error(self) -> None:
        """Test basic RouterError."""
        error = RouterError("Provider not found")
        assert str(error) == "Provider not found"
        assert error.requested_provider is None
        assert error.available_providers == []

    def test_error_with_details(self) -> None:
        """Test RouterError with provider details."""
        error = RouterError(
            "Provider 'gpt5' not found",
            requested_provider="gpt5",
            available_providers=["gpt3", "gpt4", "local"],
        )
        assert error.requested_provider == "gpt5"
        assert error.available_providers == ["gpt3", "gpt4", "local"]

    def test_error_is_exception(self) -> None:
        """Test that RouterError inherits from Exception."""
        assert isinstance(RouterError("test"), Exception)


class TestRuleBasedRouterIntentAndPriority:
    """Tests for user_intent and priority_tier routing."""

    def test_user_intent_routing(self) -> None:
        """Test routing based on user_intent."""
        providers = {
            "analytical": LocalStubProvider(provider_id="analytical"),
            "conversational": LocalStubProvider(provider_id="conversational"),
        }
        rules = {
            "analytical": "analytical",
            "conversational": "conversational",
        }
        router = RuleBasedRouter(providers, rules, default="conversational")

        selected = router.select_provider("test", metadata={"user_intent": "analytical"})
        assert selected == "analytical"

    def test_priority_tier_routing(self) -> None:
        """Test routing based on priority_tier."""
        providers = {
            "high": LocalStubProvider(provider_id="high"),
            "low": LocalStubProvider(provider_id="low"),
        }
        rules = {
            "high": "high",
            "low": "low",
        }
        router = RuleBasedRouter(providers, rules, default="low")

        selected = router.select_provider("test", metadata={"priority_tier": "high"})
        assert selected == "high"


class TestABTestRouterBasics:
    """Basic tests for ABTestRouter (existing functionality)."""

    def test_router_creation(self) -> None:
        """Test creating an ABTestRouter."""
        providers = {
            "control": LocalStubProvider(provider_id="control"),
            "treatment": LocalStubProvider(provider_id="treatment"),
        }
        router = ABTestRouter(
            providers,
            control="control",
            treatment="treatment",
            treatment_ratio=0.1,
        )
        assert router.control == "control"
        assert router.treatment == "treatment"
        assert router.treatment_ratio == 0.1

    def test_get_variant(self) -> None:
        """Test variant identification."""
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
        assert router.get_variant("control") == "control"
        assert router.get_variant("treatment") == "treatment"
        assert router.get_variant("unknown") == "unknown"
