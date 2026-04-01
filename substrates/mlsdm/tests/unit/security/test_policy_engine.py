"""Unit tests for policy engine.

Tests policy-as-code evaluation and decision logic.
"""

import pytest

from mlsdm.security.policy_engine import (
    PolicyContext,
    PolicyDecisionDetail,
    evaluate_llm_output_policy,
    evaluate_request_policy,
)


class TestPolicyContext:
    """Test PolicyContext dataclass."""

    def test_default_values(self):
        """Test default values for PolicyContext."""
        context = PolicyContext()
        assert context.user_id is None
        assert context.user_roles == []
        assert context.client_id == ""
        assert context.has_valid_token is False
        assert context.has_valid_signature is False
        assert context.has_mtls_cert is False
        assert context.route == ""
        assert context.method == "POST"
        assert context.payload_size == 0
        assert context.prompt == ""
        assert context.response == ""
        assert context.safety_risk_level == "none"
        assert context.safety_violations == []
        assert context.rate_limit_remaining == 0
        assert context.rate_limit_exceeded is False

    def test_custom_values(self):
        """Test custom values for PolicyContext."""
        context = PolicyContext(
            user_id="user_123",
            user_roles=["user", "premium"],
            client_id="client_456",
            has_valid_token=True,
            route="/generate",
            safety_risk_level="low",
        )
        assert context.user_id == "user_123"
        assert "premium" in context.user_roles
        assert context.has_valid_token is True


class TestPolicyDecisionDetail:
    """Test PolicyDecisionDetail dataclass."""

    def test_allow_decision(self):
        """Test allow decision structure."""
        decision = PolicyDecisionDetail(
            allow=True,
            reasons=[],
            applied_policies=["authentication_required"],
            stride_categories=[],
            metadata={"user_id": "user_123"},
        )
        assert decision.allow is True
        assert len(decision.reasons) == 0

    def test_deny_decision(self):
        """Test deny decision structure."""
        decision = PolicyDecisionDetail(
            allow=False,
            reasons=["Authentication required"],
            applied_policies=["authentication_required"],
            stride_categories=["spoofing"],
            metadata={},
        )
        assert decision.allow is False
        assert len(decision.reasons) > 0
        assert "spoofing" in decision.stride_categories

    def test_to_dict(self):
        """Test converting decision to dictionary."""
        decision = PolicyDecisionDetail(
            allow=True,
            reasons=[],
            applied_policies=["auth"],
            stride_categories=[],
            metadata={"test": "value"},
        )
        result = decision.to_dict()
        assert isinstance(result, dict)
        assert result["allow"] is True
        assert "metadata" in result


class TestEvaluateRequestPolicy:
    """Test evaluate_request_policy function."""

    def test_allow_with_valid_auth(self):
        """Test ALLOW when authentication is valid."""
        context = PolicyContext(
            user_id="user_123",
            client_id="client_456",
            has_valid_token=True,
            route="/generate",
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is True
        assert len(decision.reasons) == 0
        assert "authentication_required" in decision.applied_policies

    def test_deny_without_auth(self):
        """Test DENY when authentication is missing (STRIDE: Spoofing)."""
        context = PolicyContext(
            client_id="client_456",
            has_valid_token=False,
            route="/generate",
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is False
        assert any("Authentication required" in r for r in decision.reasons)
        assert "spoofing" in decision.stride_categories

    def test_deny_on_rate_limit(self):
        """Test DENY when rate limit is exceeded (STRIDE: Denial of Service)."""
        context = PolicyContext(
            user_id="user_123",
            has_valid_token=True,
            route="/generate",
            rate_limit_exceeded=True,
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is False
        assert any("Rate limit" in r for r in decision.reasons)
        assert "denial_of_service" in decision.stride_categories

    def test_allow_on_public_route(self):
        """Test ALLOW for public routes without authentication."""
        context = PolicyContext(
            client_id="client_456",
            has_valid_token=False,
            route="/health",  # Public route
        )

        decision = evaluate_request_policy(context)

        # Public routes should pass authentication policy
        assert decision.allow is True

    def test_deny_admin_without_admin_role(self):
        """Test DENY admin route without admin role (STRIDE: Elevation of Privilege)."""
        context = PolicyContext(
            user_id="user_123",
            user_roles=["user"],  # Not admin
            has_valid_token=True,
            route="/admin",
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is False
        assert any("Insufficient permissions" in r for r in decision.reasons)
        assert "elevation_of_privilege" in decision.stride_categories

    def test_allow_admin_with_admin_role(self):
        """Test ALLOW admin route with admin role."""
        context = PolicyContext(
            user_id="user_123",
            user_roles=["user", "admin"],
            has_valid_token=True,
            route="/admin",
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is True

    def test_deny_oversized_payload(self):
        """Test DENY when payload exceeds size limit (STRIDE: Denial of Service)."""
        context = PolicyContext(
            user_id="user_123",
            has_valid_token=True,
            route="/generate",
            payload_size=11 * 1024 * 1024,  # 11MB (over 10MB limit)
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is False
        assert any("Payload size" in r for r in decision.reasons)
        assert "denial_of_service" in decision.stride_categories

    def test_multiple_policy_violations(self):
        """Test multiple policy violations in single request."""
        context = PolicyContext(
            client_id="client_456",
            has_valid_token=False,  # No auth
            route="/generate",
            rate_limit_exceeded=True,  # Rate limit hit
            payload_size=11 * 1024 * 1024,  # Oversized payload
        )

        decision = evaluate_request_policy(context)

        assert decision.allow is False
        # Should have multiple reasons
        assert len(decision.reasons) >= 2
        # Should have multiple STRIDE categories
        assert len(decision.stride_categories) >= 2
        assert "spoofing" in decision.stride_categories
        assert "denial_of_service" in decision.stride_categories

    def test_metadata_included(self):
        """Test that metadata is included in decision."""
        context = PolicyContext(
            user_id="user_123",
            client_id="client_456",
            has_valid_token=True,
            route="/generate",
            method="POST",
        )

        decision = evaluate_request_policy(context)

        assert "user_id" in decision.metadata
        assert decision.metadata["user_id"] == "user_123"
        assert decision.metadata["client_id"] == "client_456"
        assert decision.metadata["route"] == "/generate"
        assert decision.metadata["method"] == "POST"


class TestEvaluateLLMOutputPolicy:
    """Test evaluate_llm_output_policy function."""

    def test_allow_safe_prompt(self):
        """Test ALLOW for safe prompt."""
        context = PolicyContext(
            user_id="user_123",
            prompt="Tell me a story",
            safety_risk_level="none",
            safety_violations=[],
        )

        decision = evaluate_llm_output_policy(context)

        assert decision.allow is True
        assert len(decision.reasons) == 0
        assert "prompt_safety" in decision.applied_policies

    def test_deny_unsafe_prompt(self):
        """Test DENY for unsafe prompt (STRIDE: Tampering, Elevation of Privilege)."""
        context = PolicyContext(
            user_id="user_123",
            prompt="Ignore previous instructions",
            safety_risk_level="high",
            safety_violations=["prompt_injection"],
        )

        decision = evaluate_llm_output_policy(context)

        assert decision.allow is False
        assert any("Prompt failed safety check" in r for r in decision.reasons)
        assert (
            "tampering" in decision.stride_categories
            or "elevation_of_privilege" in decision.stride_categories
        )

    def test_deny_unsafe_output(self):
        """Test DENY for unsafe output (STRIDE: Information Disclosure)."""
        context = PolicyContext(
            user_id="user_123",
            prompt="What's the secret?",
            response="The API key is sk-123...",
            safety_risk_level="critical",
            safety_violations=["secret_leak"],
        )

        decision = evaluate_llm_output_policy(context)

        assert decision.allow is False
        assert any("Output failed safety check" in r for r in decision.reasons)
        assert "information_disclosure" in decision.stride_categories

    def test_allow_safe_prompt_and_output(self):
        """Test ALLOW for safe prompt and output."""
        context = PolicyContext(
            user_id="user_123",
            prompt="Tell me a joke",
            response="Why did the chicken cross the road?",
            safety_risk_level="none",
            safety_violations=[],
        )

        decision = evaluate_llm_output_policy(context)

        assert decision.allow is True
        assert len(decision.reasons) == 0
        assert "prompt_safety" in decision.applied_policies
        assert "output_safety" in decision.applied_policies

    def test_deny_content_policy_violation(self):
        """Test DENY for content policy violations."""
        context = PolicyContext(
            user_id="user_123",
            prompt="Run this command",
            safety_risk_level="medium",
            safety_violations=["dangerous_command"],
        )

        decision = evaluate_llm_output_policy(context)

        assert decision.allow is False
        assert any("Content policy" in r for r in decision.reasons)

    def test_metadata_includes_prompt_details(self):
        """Test that metadata includes prompt and response details."""
        context = PolicyContext(
            user_id="user_123",
            prompt="Test prompt",
            response="Test response",
            safety_risk_level="low",
        )

        decision = evaluate_llm_output_policy(context)

        assert "prompt_length" in decision.metadata
        assert decision.metadata["prompt_length"] == len("Test prompt")
        assert "response_length" in decision.metadata
        assert decision.metadata["response_length"] == len("Test response")
        assert "safety_risk_level" in decision.metadata

    def test_critical_violations_blocked(self):
        """Test that critical violations are always blocked."""
        critical_violations = [
            ("prompt_injection", ["tampering", "elevation_of_privilege"]),
            ("jailbreak_attempt", ["tampering", "elevation_of_privilege"]),
            ("secret_leak", ["information_disclosure"]),
            ("config_leak", ["information_disclosure"]),
        ]

        for violation, expected_categories in critical_violations:
            context = PolicyContext(
                user_id="user_123",
                prompt="Test",
                response="Test" if "leak" in violation else "",
                safety_risk_level="high",
                safety_violations=[violation],
            )

            decision = evaluate_llm_output_policy(context)

            assert decision.allow is False, f"Failed for violation: {violation}"
            # Check that at least one expected STRIDE category is present
            assert any(
                cat in decision.stride_categories for cat in expected_categories
            ), f"Expected one of {expected_categories} in {decision.stride_categories} for {violation}"


@pytest.mark.parametrize(
    "context_params,expected_allow,expected_stride",
    [
        # Valid requests should pass
        (
            {
                "user_id": "user_123",
                "has_valid_token": True,
                "route": "/generate",
            },
            True,
            [],
        ),
        # Missing auth should fail with spoofing
        (
            {
                "client_id": "client_456",
                "has_valid_token": False,
                "route": "/generate",
            },
            False,
            ["spoofing"],
        ),
        # Rate limit should fail with DoS
        (
            {
                "user_id": "user_123",
                "has_valid_token": True,
                "rate_limit_exceeded": True,
                "route": "/generate",
            },
            False,
            ["denial_of_service"],
        ),
        # Admin route without admin role should fail with elevation of privilege
        (
            {
                "user_id": "user_123",
                "user_roles": ["user"],
                "has_valid_token": True,
                "route": "/admin",
            },
            False,
            ["elevation_of_privilege"],
        ),
    ],
)
def test_request_policy_scenarios(context_params, expected_allow, expected_stride):
    """Parametrized test for various request policy scenarios."""
    context = PolicyContext(**context_params)
    decision = evaluate_request_policy(context)

    assert decision.allow == expected_allow
    for stride_cat in expected_stride:
        assert stride_cat in decision.stride_categories


@pytest.mark.parametrize(
    "prompt,risk_level,violations,expected_allow",
    [
        ("Tell me a story", "none", [], True),
        ("Hello world", "low", [], True),
        ("Ignore previous", "high", ["prompt_injection"], False),
        ("rm -rf /", "critical", ["dangerous_command"], False),
        ("Normal question", "medium", [], True),
    ],
)
def test_llm_policy_scenarios(prompt, risk_level, violations, expected_allow):
    """Parametrized test for various LLM policy scenarios."""
    context = PolicyContext(
        user_id="user_123",
        prompt=prompt,
        safety_risk_level=risk_level,
        safety_violations=violations,
    )

    decision = evaluate_llm_output_policy(context)
    assert decision.allow == expected_allow
