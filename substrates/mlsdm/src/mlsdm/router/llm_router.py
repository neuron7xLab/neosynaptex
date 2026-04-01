"""
LLM Router implementations for multi-provider routing.

This module provides different routing strategies:
- RuleBasedRouter: Route based on intent, priority, mode, or other metadata
- ABTestRouter: Split traffic between control and treatment variants
"""

from __future__ import annotations

import hashlib
import logging
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mlsdm.adapters.llm_provider import LLMProvider

_logger = logging.getLogger(__name__)


class RouterError(Exception):
    """Exception raised when routing fails.

    Attributes:
        requested_provider: The provider that was requested but unavailable.
        available_providers: List of available provider names.
    """

    def __init__(
        self,
        message: str,
        requested_provider: str | None = None,
        available_providers: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.requested_provider = requested_provider
        self.available_providers = available_providers or []


class LLMRouter(ABC):
    """Abstract base class for LLM routing strategies.

    Routes requests to appropriate LLM providers based on various criteria.
    """

    def __init__(self, providers: dict[str, LLMProvider]) -> None:
        """Initialize router with available providers.

        Args:
            providers: Dictionary mapping provider names to LLMProvider instances

        Raises:
            ValueError: If providers dict is empty
        """
        if not providers:
            raise ValueError("At least one provider is required")

        self.providers = providers

    @abstractmethod
    def select_provider(self, prompt: str, metadata: dict[str, Any]) -> str:
        """Select a provider based on routing logic.

        Args:
            prompt: Input prompt text
            metadata: Request metadata (intent, priority, user_id, etc.)

        Returns:
            Provider name/key from self.providers
        """
        ...

    def get_provider(self, provider_name: str) -> LLMProvider:
        """Get provider instance by name.

        Args:
            provider_name: Provider name/key

        Returns:
            LLMProvider instance

        Raises:
            KeyError: If provider_name is not in self.providers
        """
        return self.providers[provider_name]


class RuleBasedRouter(LLMRouter):
    """Route requests based on configurable rules.

    Rules can be based on:
    - mode: Route based on mode ("cheap", "safe", "deep")
    - user_intent: Route based on intent type
    - priority_tier: Route based on priority level
    - Custom metadata fields

    Supports fallback to default provider when the selected provider is unavailable.

    Example:
        >>> providers = {
        ...     "openai_high": OpenAIProvider(),
        ...     "local_low": LocalStubProvider()
        ... }
        >>> rules = {
        ...     "deep": "openai_high",
        ...     "cheap": "local_low",
        ...     "safe": "local_low",
        ... }
        >>> router = RuleBasedRouter(providers, rules, default="local_low")
    """

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        rules: dict[str, str] | None = None,
        default: str | None = None,
        fallback_on_error: bool = True,
    ) -> None:
        """Initialize rule-based router.

        Args:
            providers: Dictionary of available providers
            rules: Mapping from metadata values to provider names
                  Example: {"deep": "openai", "cheap": "local_stub"}
            default: Default provider name if no rule matches (if None, uses first provider)
            fallback_on_error: If True, fall back to default when rule points to missing provider

        Raises:
            ValueError: If providers is empty or default provider doesn't exist
        """
        super().__init__(providers)

        self.rules = rules or {}
        self.fallback_on_error = fallback_on_error

        # Set default provider
        if default is None:
            self.default = next(iter(providers.keys()))
        else:
            if default not in providers:
                raise ValueError(f"Default provider '{default}' not found in providers")
            self.default = default

    def select_provider(self, prompt: str, metadata: dict[str, Any]) -> str:
        """Select provider based on rules.

        Checks metadata fields in order:
        1. mode (e.g., "cheap", "safe", "deep")
        2. user_intent (e.g., "high_risk", "conversational")
        3. priority_tier (e.g., "low", "medium", "high")
        4. Any other metadata keys that match rule keys

        Falls back to default provider if selected provider is unavailable
        and fallback_on_error is True.

        Args:
            prompt: Input prompt text (not used in rule-based routing)
            metadata: Request metadata with fields to match against rules

        Returns:
            Provider name

        Raises:
            RouterError: If selected provider unavailable and fallback_on_error is False
        """
        selected: str | None = None

        # Check mode first (priority routing)
        mode = metadata.get("mode")
        if mode and mode in self.rules:
            selected = self.rules[mode]

        # Check user_intent
        if selected is None:
            user_intent = metadata.get("user_intent")
            if user_intent and user_intent in self.rules:
                selected = self.rules[user_intent]

        # Check priority_tier
        if selected is None:
            priority_tier = metadata.get("priority_tier")
            if priority_tier and priority_tier in self.rules:
                selected = self.rules[priority_tier]

        # Check other metadata keys - support any hashable value type
        if selected is None:
            for _key, value in metadata.items():
                # Skip None values and check if value is a valid rule key
                if value is not None:
                    try:
                        if value in self.rules:
                            selected = self.rules[value]
                            break
                    except TypeError:
                        # Skip unhashable values (lists, dicts, etc.)
                        continue

        # Use default if nothing selected
        if selected is None:
            selected = self.default

        # Validate provider exists
        if selected not in self.providers:
            if self.fallback_on_error:
                _logger.warning(
                    "Provider '%s' not found, falling back to default '%s'",
                    selected,
                    self.default,
                )
                return self.default
            else:
                raise RouterError(
                    f"Provider '{selected}' not found in available providers",
                    requested_provider=selected,
                    available_providers=list(self.providers.keys()),
                )

        return selected


class ABTestRouter(LLMRouter):
    """Route requests for A/B testing between control and treatment variants.

    Uses consistent hashing on user_id (if provided) or random sampling
    to split traffic between control and treatment.

    Example:
        >>> providers = {
        ...     "control": OpenAIProvider(model="gpt-3.5-turbo"),
        ...     "treatment": OpenAIProvider(model="gpt-4")
        ... }
        >>> router = ABTestRouter(
        ...     providers,
        ...     control="control",
        ...     treatment="treatment",
        ...     treatment_ratio=0.1
        ... )
    """

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        control: str,
        treatment: str,
        treatment_ratio: float = 0.1,
        use_consistent_hashing: bool = True,
    ) -> None:
        """Initialize A/B test router.

        Args:
            providers: Dictionary of available providers
            control: Provider name for control variant
            treatment: Provider name for treatment variant
            treatment_ratio: Fraction of traffic to send to treatment (0.0 to 1.0)
            use_consistent_hashing: If True, use user_id for consistent hashing
                                   If False, use random sampling

        Raises:
            ValueError: If control or treatment providers don't exist,
                       or if treatment_ratio is invalid
        """
        super().__init__(providers)

        if control not in providers:
            raise ValueError(f"Control provider '{control}' not found in providers")
        if treatment not in providers:
            raise ValueError(f"Treatment provider '{treatment}' not found in providers")

        if not 0.0 <= treatment_ratio <= 1.0:
            raise ValueError(f"treatment_ratio must be between 0.0 and 1.0, got {treatment_ratio}")

        self.control = control
        self.treatment = treatment
        self.treatment_ratio = treatment_ratio
        self.use_consistent_hashing = use_consistent_hashing

    def select_provider(self, prompt: str, metadata: dict[str, Any]) -> str:
        """Select provider using A/B test logic.

        Uses consistent hashing if user_id is provided and use_consistent_hashing=True,
        otherwise uses random sampling.

        Args:
            prompt: Input prompt text (not used in A/B routing)
            metadata: Request metadata, should include user_id for consistent hashing

        Returns:
            Provider name (control or treatment)
        """
        if self.treatment_ratio == 0.0:
            return self.control

        if self.treatment_ratio == 1.0:
            return self.treatment

        # Use consistent hashing if user_id provided
        if self.use_consistent_hashing and "user_id" in metadata:
            user_id = str(metadata["user_id"])
            # Hash user_id to get deterministic assignment
            hash_value = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
            # Normalize to [0, 1)
            normalized = (hash_value % 1_000_000) / 1_000_000

            if normalized < self.treatment_ratio:
                return self.treatment
            return self.control

        # Random sampling
        if random.random() < self.treatment_ratio:
            return self.treatment
        return self.control

    def get_variant(self, provider_name: str) -> str:
        """Get variant name (control/treatment) for a provider.

        Args:
            provider_name: Provider name

        Returns:
            "control" or "treatment"
        """
        if provider_name == self.control:
            return "control"
        elif provider_name == self.treatment:
            return "treatment"
        else:
            return "unknown"
