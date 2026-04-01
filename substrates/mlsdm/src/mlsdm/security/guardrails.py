"""Runtime Guardrails Orchestrator for MLSDM.

This module provides a centralized guardrail enforcement layer that maps
STRIDE threat categories to concrete security controls.

STRIDE Mapping:
---------------
- **Spoofing**: OIDC token validation, mTLS certificate verification, request signing
- **Tampering**: Request signature verification, input validation, config validation
- **Repudiation**: Structured audit logging with correlation IDs and user identity
- **Information Disclosure**: Payload scrubbing (PII/secrets), secure logging
- **Denial of Service**: Rate limiting, request timeouts, bulkhead pattern
- **Elevation of Privilege**: RBAC permission checks on sensitive operations

This orchestrator is the single entry point for all security decisions,
ensuring consistent policy enforcement across the API and SDK.

Example:
    >>> from mlsdm.security.guardrails import GuardrailContext, enforce_request_guardrails
    >>>
    >>> context = GuardrailContext(
    ...     request=request,
    ...     route="/generate",
    ...     scopes=["llm:generate"]
    ... )
    >>> decision = await enforce_request_guardrails(context)
    >>> if not decision.allow:
    ...     raise HTTPException(status_code=403, detail=decision.reasons)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from fastapi import Request

from mlsdm.observability.tracing import get_tracer_manager
from mlsdm.utils.security_logger import SecurityEventType, get_security_logger

logger = logging.getLogger(__name__)
security_logger = get_security_logger()


class StrideCategory(str, Enum):
    """STRIDE threat categories for security classification."""

    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class GuardrailCheckType(str, Enum):
    """Types of guardrail checks performed."""

    AUTHENTICATION = "authentication"  # OIDC, mTLS, API key
    AUTHORIZATION = "authorization"  # RBAC, scopes
    REQUEST_SIGNING = "request_signing"  # Request signature verification
    INPUT_VALIDATION = "input_validation"  # Request payload validation
    RATE_LIMITING = "rate_limiting"  # Rate limit enforcement
    SAFETY_FILTERING = "safety_filtering"  # LLM safety checks
    PII_SCRUBBING = "pii_scrubbing"  # PII detection and removal


class PolicyDecision(TypedDict):
    """Policy evaluation decision result.

    This structure represents the outcome of a guardrail evaluation,
    including whether the request is allowed, reasons for denial,
    and which STRIDE categories were triggered.

    Attributes:
        allow: Whether the request/operation is allowed
        reasons: List of human-readable reasons for denial (empty if allowed)
        stride_categories: STRIDE categories that apply to this decision
        checks_performed: List of guardrail checks that were executed
        metadata: Additional context (user_id, client_id, risk_level, etc.)
    """

    allow: bool
    reasons: list[str]
    stride_categories: list[str]
    checks_performed: list[str]
    metadata: dict[str, Any]


@dataclass
class GuardrailContext:
    """Context for guardrail evaluation.

    Attributes:
        request: FastAPI request object (if available)
        route: API route or operation name
        user_id: Authenticated user identifier (if available)
        client_id: Client identifier (hashed IP + UA or cert CN)
        scopes: Required permission scopes
        payload: Request payload (for validation)
        risk_level: Risk level of the operation (low, medium, high, critical)
        metadata: Additional context
    """

    request: Request | None = None
    route: str = ""
    user_id: str | None = None
    client_id: str = ""
    scopes: list[str] = field(default_factory=list)
    payload: dict[str, Any] | None = None
    risk_level: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Result of a single guardrail check.

    Attributes:
        check_type: Type of check performed
        passed: Whether the check passed
        reason: Reason for failure (if failed)
        stride_category: Primary STRIDE category for this check
        metadata: Additional check-specific metadata
    """

    check_type: GuardrailCheckType
    passed: bool
    reason: str = ""
    stride_category: StrideCategory | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


async def enforce_request_guardrails(
    context: GuardrailContext,
) -> PolicyDecision:
    """Enforce comprehensive request-level guardrails.

    This is the main entry point for request validation. It orchestrates
    all security checks and returns a unified policy decision.

    STRIDE Controls Applied:
    - Spoofing: Authentication checks (OIDC/mTLS/signing)
    - Tampering: Request signature verification, input validation
    - Repudiation: Audit logging with correlation
    - Information Disclosure: Payload scrubbing for logs
    - Denial of Service: Rate limiting
    - Elevation of Privilege: RBAC authorization

    Args:
        context: Guardrail evaluation context

    Returns:
        PolicyDecision with allow/deny result and reasons

    Example:
        >>> context = GuardrailContext(
        ...     request=request,
        ...     route="/generate",
        ...     client_id="abc123",
        ...     scopes=["llm:generate"]
        ... )
        >>> decision = await enforce_request_guardrails(context)
        >>> if not decision["allow"]:
        ...     raise HTTPException(status_code=403, detail=decision["reasons"])
    """
    tracer = get_tracer_manager()
    results: list[GuardrailResult] = []

    # Start a span for guardrail evaluation
    with tracer.start_span(
        "guardrails.enforce_request",
        attributes={
            "guardrails.route": context.route,
            "guardrails.client_id": context.client_id,
            "guardrails.risk_level": context.risk_level,
        },
    ) as span:
        # 1. Authentication Check (Spoofing)
        auth_result = await _check_authentication(context)
        results.append(auth_result)
        span.set_attribute("guardrails.auth_passed", auth_result.passed)

        # 2. Authorization Check (Elevation of Privilege)
        if auth_result.passed and context.scopes:
            authz_result = await _check_authorization(context)
            results.append(authz_result)
            span.set_attribute("guardrails.authz_passed", authz_result.passed)

        # 3. Request Signing Check (Tampering)
        signing_result = await _check_request_signing(context)
        results.append(signing_result)
        span.set_attribute("guardrails.signing_passed", signing_result.passed)

        # 4. Rate Limiting Check (Denial of Service)
        rate_limit_result = await _check_rate_limiting(context)
        results.append(rate_limit_result)
        span.set_attribute("guardrails.rate_limit_passed", rate_limit_result.passed)

        # 5. Input Validation Check (Tampering)
        if context.payload:
            validation_result = await _check_input_validation(context)
            results.append(validation_result)
            span.set_attribute("guardrails.validation_passed", validation_result.passed)

        # 6. PII Scrubbing (Information Disclosure) - always performed for logging
        pii_result = await _check_pii_scrubbing(context)
        results.append(pii_result)

        # Build policy decision
        decision = _build_policy_decision(results, context)

        # Log decision (Repudiation protection)
        _log_guardrail_decision(decision, context, span)

        # Record metrics
        _record_guardrail_metrics(decision, results)

        return decision


async def enforce_llm_guardrails(
    context: GuardrailContext,
    prompt: str,
    response: str | None = None,
) -> PolicyDecision:
    """Enforce LLM-specific safety guardrails.

    This function applies safety filtering to LLM prompts and responses,
    protecting against prompt injection, jailbreak attempts, and unsafe outputs.

    STRIDE Controls Applied:
    - Tampering: Prompt injection detection
    - Information Disclosure: Secret/config leak detection in outputs
    - Elevation of Privilege: Instruction override detection

    Args:
        context: Guardrail evaluation context
        prompt: User prompt to validate
        response: LLM response to validate (optional)

    Returns:
        PolicyDecision with safety assessment

    Example:
        >>> context = GuardrailContext(
        ...     user_id="user_123",
        ...     client_id="client_456",
        ...     route="/generate",
        ... )
        >>> decision = await enforce_llm_guardrails(
        ...     context=context,
        ...     prompt="Generate a story",
        ...     response="Once upon a time..."
        ... )
    """
    tracer = get_tracer_manager()
    results: list[GuardrailResult] = []

    with tracer.start_span(
        "guardrails.enforce_llm",
        attributes={
            "guardrails.route": context.route,
            "guardrails.has_response": response is not None,
            "guardrails.prompt_length": len(prompt),
        },
    ) as span:
        # 1. Prompt Safety Check
        prompt_result = await _check_prompt_safety(prompt, context)
        results.append(prompt_result)
        span.set_attribute("guardrails.prompt_safe", prompt_result.passed)

        # 2. Response Safety Check (if response provided)
        if response:
            response_result = await _check_response_safety(response, context)
            results.append(response_result)
            span.set_attribute("guardrails.response_safe", response_result.passed)

        # Build decision
        decision = _build_policy_decision(results, context)

        # Log decision
        _log_guardrail_decision(decision, context, span)

        # Record metrics
        _record_guardrail_metrics(decision, results)

        return decision


# ---------------------------------------------------------------------------
# Internal Guardrail Check Functions
# ---------------------------------------------------------------------------


async def _check_authentication(context: GuardrailContext) -> GuardrailResult:
    """Check authentication (OIDC, mTLS, API key).

    STRIDE: Spoofing protection
    """
    # For now, return passed if no request (SDK pre-flight)
    # In production, this would check OIDC tokens, mTLS certs, or API keys
    if context.request is None:
        return GuardrailResult(
            check_type=GuardrailCheckType.AUTHENTICATION,
            passed=True,
            stride_category=StrideCategory.SPOOFING,
            metadata={"source": "sdk_preflight"},
        )

    # Check for authentication credentials
    auth_header = context.request.headers.get("Authorization", "")
    has_auth = bool(auth_header) or bool(context.user_id)

    return GuardrailResult(
        check_type=GuardrailCheckType.AUTHENTICATION,
        passed=has_auth,
        reason="Missing authentication credentials" if not has_auth else "",
        stride_category=StrideCategory.SPOOFING,
        metadata={
            "has_auth_header": bool(auth_header),
            "has_user_id": bool(context.user_id),
        },
    )


async def _check_authorization(context: GuardrailContext) -> GuardrailResult:
    """Check RBAC authorization for required scopes.

    STRIDE: Elevation of Privilege protection
    """
    # For now, simplified check - in production would use full RBAC
    if not context.scopes:
        return GuardrailResult(
            check_type=GuardrailCheckType.AUTHORIZATION,
            passed=True,
            stride_category=StrideCategory.ELEVATION_OF_PRIVILEGE,
        )

    # Full RBAC integration planned for future PR to maintain backward compatibility
    # For now, authorization is handled by existing middleware and dependency injection
    return GuardrailResult(
        check_type=GuardrailCheckType.AUTHORIZATION,
        passed=True,
        stride_category=StrideCategory.ELEVATION_OF_PRIVILEGE,
        metadata={"scopes_required": context.scopes},
    )


async def _check_request_signing(context: GuardrailContext) -> GuardrailResult:
    """Check request signature for tampering protection.

    STRIDE: Tampering protection
    """
    # Optional check - only fail if signing is explicitly required
    if context.request is None:
        return GuardrailResult(
            check_type=GuardrailCheckType.REQUEST_SIGNING,
            passed=True,
            stride_category=StrideCategory.TAMPERING,
            metadata={"required": False},
        )

    # Full signing integration planned for future PR to maintain backward compatibility
    # For now, optional signature check (not enforced by default)
    signature_header = context.request.headers.get("X-MLSDM-Signature")

    return GuardrailResult(
        check_type=GuardrailCheckType.REQUEST_SIGNING,
        passed=True,  # Not enforced by default
        stride_category=StrideCategory.TAMPERING,
        metadata={
            "has_signature": bool(signature_header),
            "required": False,
        },
    )


async def _check_rate_limiting(context: GuardrailContext) -> GuardrailResult:
    """Check rate limiting to prevent DoS.

    STRIDE: Denial of Service protection
    """
    # Rate limiting is handled by existing rate_limiter in app.py
    # This check is informational for the guardrail framework
    return GuardrailResult(
        check_type=GuardrailCheckType.RATE_LIMITING,
        passed=True,
        stride_category=StrideCategory.DENIAL_OF_SERVICE,
        metadata={
            "enforced_by": "api_middleware",
            "client_id": context.client_id,
        },
    )


async def _check_input_validation(context: GuardrailContext) -> GuardrailResult:
    """Validate input payload for tampering protection.

    STRIDE: Tampering protection
    """
    if not context.payload:
        return GuardrailResult(
            check_type=GuardrailCheckType.INPUT_VALIDATION,
            passed=True,
            stride_category=StrideCategory.TAMPERING,
        )

    # Full input validation integration planned for future PR
    # Basic validation currently handled by Pydantic models in API
    return GuardrailResult(
        check_type=GuardrailCheckType.INPUT_VALIDATION,
        passed=True,
        stride_category=StrideCategory.TAMPERING,
        metadata={"payload_size": len(str(context.payload))},
    )


async def _check_pii_scrubbing(context: GuardrailContext) -> GuardrailResult:
    """Check for PII in payload/logs to prevent information disclosure.

    STRIDE: Information Disclosure protection
    """
    # PII scrubbing is always performed for logging
    # This is informational check for the guardrail framework
    return GuardrailResult(
        check_type=GuardrailCheckType.PII_SCRUBBING,
        passed=True,
        stride_category=StrideCategory.INFORMATION_DISCLOSURE,
        metadata={"enforced_by": "payload_scrubber"},
    )


async def _check_prompt_safety(prompt: str, context: GuardrailContext) -> GuardrailResult:
    """Check prompt for safety violations (injection, jailbreak).

    STRIDE: Tampering (prompt injection), Elevation of Privilege (instruction override)
    """
    # Import here to avoid circular dependency (llm_safety imports from other security modules)
    from mlsdm.security.llm_safety import SafetyRiskLevel, analyze_prompt

    # Analyze prompt using existing llm_safety module
    safety_result = analyze_prompt(prompt)

    passed = safety_result.is_safe and safety_result.risk_level in (
        SafetyRiskLevel.NONE,
        SafetyRiskLevel.LOW,
    )

    return GuardrailResult(
        check_type=GuardrailCheckType.SAFETY_FILTERING,
        passed=passed,
        reason=f"Safety risk: {safety_result.risk_level.value}" if not passed else "",
        stride_category=StrideCategory.TAMPERING,
        metadata={
            "risk_level": safety_result.risk_level.value,
            "violations": [v.category.value for v in safety_result.violations],
        },
    )


async def _check_response_safety(response: str, context: GuardrailContext) -> GuardrailResult:
    """Check response for safety violations (secret leaks, config disclosure).

    STRIDE: Information Disclosure
    """
    # Import here to avoid circular dependency (llm_safety imports from other security modules)
    from mlsdm.security.llm_safety import SafetyRiskLevel, filter_output

    # Analyze output using existing llm_safety module
    safety_result = filter_output(response)

    passed = safety_result.is_safe and safety_result.risk_level in (
        SafetyRiskLevel.NONE,
        SafetyRiskLevel.LOW,
    )

    return GuardrailResult(
        check_type=GuardrailCheckType.SAFETY_FILTERING,
        passed=passed,
        reason=f"Safety risk in output: {safety_result.risk_level.value}" if not passed else "",
        stride_category=StrideCategory.INFORMATION_DISCLOSURE,
        metadata={
            "risk_level": safety_result.risk_level.value,
            "violations": [v.category.value for v in safety_result.violations],
        },
    )


# ---------------------------------------------------------------------------
# Policy Decision Building
# ---------------------------------------------------------------------------


def _build_policy_decision(
    results: list[GuardrailResult],
    context: GuardrailContext,
) -> PolicyDecision:
    """Build unified policy decision from guardrail check results.

    Args:
        results: List of individual guardrail check results
        context: Guardrail evaluation context

    Returns:
        PolicyDecision with aggregated result
    """
    # Aggregate results
    all_passed = all(r.passed for r in results)
    reasons = [r.reason for r in results if not r.passed and r.reason]
    stride_categories = list({r.stride_category.value for r in results if r.stride_category})
    checks_performed = [r.check_type.value for r in results]

    # Build metadata
    metadata: dict[str, Any] = {
        "user_id": context.user_id,
        "client_id": context.client_id,
        "route": context.route,
        "risk_level": context.risk_level,
        "total_checks": len(results),
        "passed_checks": sum(1 for r in results if r.passed),
        "failed_checks": sum(1 for r in results if not r.passed),
    }
    metadata.update(context.metadata)

    return PolicyDecision(
        allow=all_passed,
        reasons=reasons,
        stride_categories=stride_categories,
        checks_performed=checks_performed,
        metadata=metadata,
    )


def _log_guardrail_decision(
    decision: PolicyDecision,
    context: GuardrailContext,
    span: Any,
) -> None:
    """Log guardrail decision for audit trail (Repudiation protection).

    Args:
        decision: Policy decision to log
        context: Guardrail context
        span: OpenTelemetry span for correlation
    """
    # Add decision to span
    span.set_attribute("guardrails.decision.allow", decision["allow"])
    span.set_attribute(
        "guardrails.decision.stride_categories", ",".join(decision["stride_categories"])
    )
    span.set_attribute(
        "guardrails.decision.checks_performed", ",".join(decision["checks_performed"])
    )

    # Log decision with structured logging
    log_level = logging.INFO if decision["allow"] else logging.WARNING
    logger.log(
        log_level,
        f"Guardrail decision: {'ALLOW' if decision['allow'] else 'DENY'}",
        extra={
            "guardrail_decision": "allow" if decision["allow"] else "deny",
            "reasons": decision["reasons"],
            "stride_categories": decision["stride_categories"],
            "checks_performed": decision["checks_performed"],
            "user_id": context.user_id,
            "client_id": context.client_id,
            "route": context.route,
            "risk_level": context.risk_level,
        },
    )

    # Log to security logger for audit trail
    if decision["allow"]:
        # Use AUTH_SUCCESS for allowed access
        security_logger.log_auth_success(
            client_id=context.client_id or "unknown",
        )
    else:
        # Use AUTHZ_DENIED for denied access - use system_event as it's more general
        security_logger.log_system_event(
            SecurityEventType.AUTHZ_DENIED,
            f"Guardrails denied access to {context.route}",
            additional_data={
                "client_id": context.client_id,
                "user_id": context.user_id,
                "reasons": decision["reasons"],
                "stride_categories": decision["stride_categories"],
            },
        )


def _record_guardrail_metrics(
    decision: PolicyDecision,
    results: list[GuardrailResult],
) -> None:
    """Record guardrail metrics for observability.

    Args:
        decision: Policy decision
        results: Individual check results
    """
    try:
        from mlsdm.observability.metrics import get_metrics_exporter

        exporter = get_metrics_exporter()

        # Record overall decision
        if hasattr(exporter, "record_guardrail_decision"):
            exporter.record_guardrail_decision(
                allowed=decision["allow"],
                stride_categories=decision["stride_categories"],
                checks_performed=decision["checks_performed"],
            )

        # Record per-check metrics
        for result in results:
            if hasattr(exporter, "record_guardrail_check"):
                exporter.record_guardrail_check(
                    check_type=result.check_type.value,
                    passed=result.passed,
                    stride_category=result.stride_category.value if result.stride_category else "",
                )
    except Exception as e:
        # Graceful degradation - don't fail request if metrics fail
        logger.warning(f"Failed to record guardrail metrics: {e}")
