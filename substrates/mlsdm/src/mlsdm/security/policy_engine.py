"""Policy-as-Code Engine for MLSDM.

This module provides a declarative policy evaluation engine that promotes
security and governance decisions from scattered if/else logic into explicit,
testable policies.

Design Principles:
------------------
- Policies are deterministic and testable
- Policy decisions are logged and observable
- Policies are composable and reusable
- Policy failures are expressive (explain why denial occurred)

Example:
    >>> from mlsdm.security.policy_engine import evaluate_request_policy
    >>>
    >>> context = PolicyContext(
    ...     user_roles=["user"],
    ...     client_id="abc123",
    ...     route="/generate",
    ...     has_valid_token=True,
    ... )
    >>> decision = evaluate_request_policy(context)
    >>> if not decision.allow:
    ...     raise HTTPException(status_code=403, detail=decision.reasons)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Policy configuration constants (can be overridden via environment)
MAX_PAYLOAD_SIZE = int(os.getenv("MLSDM_MAX_PAYLOAD_SIZE", str(10 * 1024 * 1024)))  # 10MB default


@dataclass
class PolicyContext:
    """Context for policy evaluation.

    This structure contains all the inputs needed to evaluate security
    and governance policies.

    Attributes:
        # Identity and Authentication
        user_id: Authenticated user identifier
        user_roles: User roles/permissions
        client_id: Client identifier (hashed)
        has_valid_token: Whether valid auth token is present
        has_valid_signature: Whether valid request signature is present
        has_mtls_cert: Whether valid mTLS certificate is present

        # Request Context
        route: API route or operation
        method: HTTP method (GET, POST, etc.)
        payload_size: Size of request payload in bytes
        request_headers: Request headers

        # Safety Context
        prompt: User prompt (for LLM operations)
        response: LLM response (for output filtering)
        safety_risk_level: Safety risk level (none, low, medium, high, critical)
        safety_violations: List of safety violation categories

        # Rate Limiting Context
        rate_limit_remaining: Remaining rate limit quota
        rate_limit_exceeded: Whether rate limit was exceeded

        # Additional Metadata
        metadata: Additional context for policy evaluation
    """

    # Identity and Authentication
    user_id: str | None = None
    user_roles: list[str] = field(default_factory=list)
    client_id: str = ""
    has_valid_token: bool = False
    has_valid_signature: bool = False
    has_mtls_cert: bool = False

    # Request Context
    route: str = ""
    method: str = "POST"
    payload_size: int = 0
    request_headers: dict[str, str] = field(default_factory=dict)

    # Safety Context
    prompt: str = ""
    response: str = ""
    safety_risk_level: str = "none"
    safety_violations: list[str] = field(default_factory=list)

    # Rate Limiting Context
    rate_limit_remaining: int = 0
    rate_limit_exceeded: bool = False

    # Additional Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecisionDetail:
    """Detailed policy decision result.

    Attributes:
        allow: Whether the operation is allowed
        reasons: List of reasons for denial (empty if allowed)
        applied_policies: List of policy names that were evaluated
        stride_categories: STRIDE categories relevant to this decision
        metadata: Additional decision metadata
    """

    allow: bool
    reasons: list[str] = field(default_factory=list)
    applied_policies: list[str] = field(default_factory=list)
    stride_categories: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "allow": self.allow,
            "reasons": self.reasons,
            "applied_policies": self.applied_policies,
            "stride_categories": self.stride_categories,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Request Policy Evaluation
# ---------------------------------------------------------------------------


def evaluate_request_policy(context: PolicyContext) -> PolicyDecisionDetail:
    """Evaluate comprehensive request-level policy.

    This function evaluates all request-level policies and returns
    a unified decision. Policies are evaluated in order of importance:
    1. Authentication (must have valid credentials)
    2. Rate limiting (must not exceed quota)
    3. Authorization (must have required roles/permissions)
    4. Request integrity (signature validation, if required)

    Args:
        context: Policy evaluation context

    Returns:
        PolicyDecisionDetail with allow/deny result

    Example:
        >>> context = PolicyContext(
        ...     user_id="user_123",
        ...     user_roles=["user"],
        ...     client_id="client_456",
        ...     has_valid_token=True,
        ...     route="/generate",
        ... )
        >>> decision = evaluate_request_policy(context)
        >>> assert decision.allow is True
    """
    reasons: list[str] = []
    applied_policies: list[str] = []
    stride_categories: list[str] = []

    # Policy 1: Authentication Required
    # STRIDE: Spoofing
    if not _policy_authentication_required(context):
        reasons.append("Authentication required but not provided")
        stride_categories.append("spoofing")
    applied_policies.append("authentication_required")

    # Policy 2: Rate Limiting
    # STRIDE: Denial of Service
    if context.rate_limit_exceeded:
        reasons.append("Rate limit exceeded")
        stride_categories.append("denial_of_service")
    applied_policies.append("rate_limiting")

    # Policy 3: Authorization for Sensitive Routes
    # STRIDE: Elevation of Privilege
    if not _policy_authorization_for_route(context):
        reasons.append(f"Insufficient permissions for route: {context.route}")
        stride_categories.append("elevation_of_privilege")
    applied_policies.append("route_authorization")

    # Policy 4: Request Signature (for high-security routes)
    # STRIDE: Tampering
    if _requires_request_signature(context.route) and not context.has_valid_signature:
        reasons.append("Request signature required but not provided or invalid")
        stride_categories.append("tampering")
    applied_policies.append("request_signature")

    # Policy 5: Payload Size Limit
    # STRIDE: Denial of Service
    if not _policy_payload_size_limit(context):
        reasons.append(f"Payload size {context.payload_size} exceeds maximum allowed")
        stride_categories.append("denial_of_service")
    applied_policies.append("payload_size_limit")

    # Build decision
    allow = len(reasons) == 0
    metadata = {
        "user_id": context.user_id,
        "client_id": context.client_id,
        "route": context.route,
        "method": context.method,
    }

    return PolicyDecisionDetail(
        allow=allow,
        reasons=reasons,
        applied_policies=applied_policies,
        stride_categories=list(set(stride_categories)),
        metadata=metadata,
    )


def evaluate_llm_output_policy(context: PolicyContext) -> PolicyDecisionDetail:
    """Evaluate LLM output-level policy.

    This function evaluates policies specific to LLM operations,
    including prompt safety and output filtering.

    Policies evaluated:
    1. Prompt safety (injection/jailbreak detection)
    2. Output safety (secret/config leak detection)
    3. Content policy compliance

    Args:
        context: Policy evaluation context with prompt and response

    Returns:
        PolicyDecisionDetail with safety assessment

    Example:
        >>> context = PolicyContext(
        ...     user_id="user_123",
        ...     prompt="Tell me a story",
        ...     response="Once upon a time...",
        ...     safety_risk_level="none",
        ... )
        >>> decision = evaluate_llm_output_policy(context)
        >>> assert decision.allow is True
    """
    reasons: list[str] = []
    applied_policies: list[str] = []
    stride_categories: list[str] = []

    # Policy 1: Prompt Safety
    # STRIDE: Tampering (prompt injection), Elevation of Privilege
    if not _policy_prompt_safety(context):
        reasons.append(f"Prompt failed safety check: {context.safety_risk_level}")
        stride_categories.extend(["tampering", "elevation_of_privilege"])
    applied_policies.append("prompt_safety")

    # Policy 2: Output Safety
    # STRIDE: Information Disclosure
    if context.response and not _policy_output_safety(context):
        reasons.append(f"Output failed safety check: {context.safety_risk_level}")
        stride_categories.append("information_disclosure")
    applied_policies.append("output_safety")

    # Policy 3: Content Policy Compliance
    # STRIDE: Multiple categories depending on violation
    if not _policy_content_compliance(context):
        reasons.append("Content policy violations detected")
        stride_categories.extend(["tampering", "information_disclosure"])
    applied_policies.append("content_compliance")

    # Build decision
    allow = len(reasons) == 0
    metadata = {
        "user_id": context.user_id,
        "prompt_length": len(context.prompt),
        "response_length": len(context.response) if context.response else 0,
        "safety_risk_level": context.safety_risk_level,
        "safety_violations": context.safety_violations,
    }

    return PolicyDecisionDetail(
        allow=allow,
        reasons=reasons,
        applied_policies=applied_policies,
        stride_categories=list(set(stride_categories)),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Individual Policy Functions
# ---------------------------------------------------------------------------


def _policy_authentication_required(context: PolicyContext) -> bool:
    """Policy: Authentication is required for all non-public routes.

    STRIDE: Spoofing protection

    Returns:
        True if authenticated or route is public, False otherwise
    """
    # Public routes that don't require authentication
    public_routes = [
        "/health",
        "/health/live",
        "/health/ready",
        "/status",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    if context.route in public_routes:
        return True

    # Must have at least one form of authentication
    return context.has_valid_token or context.has_mtls_cert


def _policy_authorization_for_route(context: PolicyContext) -> bool:
    """Policy: User must have required role/permission for route.

    STRIDE: Elevation of Privilege protection

    Returns:
        True if authorized or route doesn't require specific roles
    """
    # Define route -> required role mapping
    route_role_map = {
        "/admin": ["admin"],
        "/v1/admin": ["admin"],
    }

    required_roles = route_role_map.get(context.route, [])
    if not required_roles:
        return True  # No specific roles required

    # Check if user has any of the required roles
    return any(role in context.user_roles for role in required_roles)


def _requires_request_signature(route: str) -> bool:
    """Check if route requires request signature.

    High-security routes that modify system state should require signatures.
    Currently optional for all routes to maintain backward compatibility.

    Args:
        route: API route

    Returns:
        True if signature is required

    Note:
        Signature requirements are disabled by default for backward compatibility.
        Enable by setting MLSDM_REQUIRE_SIGNATURES=true and configure routes
        in MLSDM_SIGNATURE_REQUIRED_ROUTES env var (comma-separated).
    """
    # Check if signature requirement is enabled globally
    require_sigs = os.getenv("MLSDM_REQUIRE_SIGNATURES", "false").lower() == "true"
    if not require_sigs:
        return False

    # Get routes from environment (comma-separated)
    routes_str = os.getenv("MLSDM_SIGNATURE_REQUIRED_ROUTES", "")
    signature_required_routes = [r.strip() for r in routes_str.split(",") if r.strip()]

    return route in signature_required_routes


def _policy_payload_size_limit(context: PolicyContext) -> bool:
    """Policy: Request payload must not exceed size limit.

    STRIDE: Denial of Service protection

    Returns:
        True if payload size is within limits
    """
    return context.payload_size <= MAX_PAYLOAD_SIZE


def _policy_prompt_safety(context: PolicyContext) -> bool:
    """Policy: Prompt must pass safety checks.

    STRIDE: Tampering, Elevation of Privilege

    Returns:
        True if prompt is safe
    """
    if not context.prompt:
        return True  # No prompt to check

    # Check risk level
    unsafe_levels = ["high", "critical"]
    if context.safety_risk_level in unsafe_levels:
        return False

    # Check for specific violations
    critical_violations = [
        "prompt_injection",
        "jailbreak_attempt",
        "instruction_override",
        "role_hijack",
    ]

    has_critical_violation = any(v in context.safety_violations for v in critical_violations)

    return not has_critical_violation


def _policy_output_safety(context: PolicyContext) -> bool:
    """Policy: LLM output must pass safety checks.

    STRIDE: Information Disclosure

    Returns:
        True if output is safe
    """
    if not context.response:
        return True  # No response to check

    # Check risk level
    unsafe_levels = ["high", "critical"]
    if context.safety_risk_level in unsafe_levels:
        return False

    # Check for specific violations
    critical_violations = [
        "secret_leak",
        "config_leak",
        "system_prompt_probe",
    ]

    has_critical_violation = any(v in context.safety_violations for v in critical_violations)

    return not has_critical_violation


def _policy_content_compliance(context: PolicyContext) -> bool:
    """Policy: Content must comply with content policy.

    STRIDE: Multiple categories

    Returns:
        True if content complies
    """
    # For now, rely on safety violations
    # In production, this would integrate with content moderation APIs

    # Check for dangerous commands or patterns
    dangerous_violations = [
        "dangerous_command",
    ]

    has_dangerous_violation = any(v in context.safety_violations for v in dangerous_violations)

    return not has_dangerous_violation
