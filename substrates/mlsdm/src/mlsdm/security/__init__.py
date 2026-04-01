"""
MLSDM Security: Security utilities for the NeuroCognitiveEngine.

This module provides security features including rate limiting,
payload scrubbing, OIDC authentication, RBAC, and logging controls.
"""

from mlsdm.security.llm_safety import (
    ConversationAnalysisResult,
    LLMSafetyAnalyzer,
    SafetyCategory,
    SafetyResult,
    SafetyRiskLevel,
    SafetyViolation,
    SanitizedContext,
    analyze_conversation_patterns,
    analyze_prompt,
    filter_output,
    get_llm_safety_analyzer,
    sanitize_context,
    sanitize_context_for_llm,
)
from mlsdm.security.oidc import (
    OIDCAuthenticator,
    OIDCAuthMiddleware,
    OIDCConfig,
    UserInfo,
    get_current_user,
    get_optional_user,
    require_oidc_auth,
)
from mlsdm.security.payload_scrubber import (
    DEFAULT_SECRET_KEYS,
    EMAIL_PATTERN,
    FORBIDDEN_FIELDS,
    PII_FIELDS,
    SECRET_PATTERNS,
    is_secure_mode,
    scrub_dict,
    scrub_log_record,
    scrub_request_payload,
    scrub_text,
    should_log_payload,
)
from mlsdm.security.rate_limit import RateLimiter, get_rate_limiter

__all__ = [
    "RateLimiter",
    "get_rate_limiter",
    "scrub_text",
    "scrub_dict",
    "scrub_request_payload",
    "scrub_log_record",
    "should_log_payload",
    "is_secure_mode",
    "SECRET_PATTERNS",
    "PII_FIELDS",
    "FORBIDDEN_FIELDS",
    "EMAIL_PATTERN",
    "DEFAULT_SECRET_KEYS",
    # OIDC (SEC-004)
    "OIDCAuthenticator",
    "OIDCAuthMiddleware",
    "OIDCConfig",
    "UserInfo",
    "get_current_user",
    "get_optional_user",
    "require_oidc_auth",
    # LLM Safety (R003, R018)
    "LLMSafetyAnalyzer",
    "SafetyCategory",
    "SafetyResult",
    "SafetyRiskLevel",
    "SafetyViolation",
    "analyze_prompt",
    "filter_output",
    "get_llm_safety_analyzer",
    # Multi-turn attack detection (R003)
    "ConversationAnalysisResult",
    "analyze_conversation_patterns",
    # Context sanitization (R018)
    "SanitizedContext",
    "sanitize_context",
    "sanitize_context_for_llm",
]
