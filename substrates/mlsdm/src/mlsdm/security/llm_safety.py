"""LLM Safety Module for MLSDM.

This module provides comprehensive safety measures for LLM interactions:
1. Prompt injection detection and prevention
2. Output filtering for secret/config leakage
3. Jailbreak attempt detection
4. Content policy enforcement

Implements SEC-004 requirements from PROD_GAPS.md.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SafetyRiskLevel(Enum):
    """Risk levels for safety analysis."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyCategory(Enum):
    """Categories of safety violations."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    SECRET_LEAK = "secret_leak"
    CONFIG_LEAK = "config_leak"
    SYSTEM_PROMPT_PROBE = "system_prompt_probe"
    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_HIJACK = "role_hijack"
    DANGEROUS_COMMAND = "dangerous_command"


@dataclass
class SafetyResult:
    """Result of safety analysis.

    Attributes:
        is_safe: Whether the input/output is considered safe
        risk_level: Overall risk level
        violations: List of detected safety violations
        sanitized_content: Content with dangerous patterns removed (if applicable)
        metadata: Additional analysis metadata
    """

    is_safe: bool
    risk_level: SafetyRiskLevel = SafetyRiskLevel.NONE
    violations: list[SafetyViolation] = field(default_factory=list)
    sanitized_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_safe": self.is_safe,
            "risk_level": self.risk_level.value,
            "violations": [v.to_dict() for v in self.violations],
            "metadata": self.metadata,
        }


@dataclass
class SafetyViolation:
    """Represents a single safety violation.

    Attributes:
        category: Type of violation
        pattern: Pattern that was matched
        severity: Severity score (0.0-1.0)
        description: Human-readable description
    """

    category: SafetyCategory
    pattern: str
    severity: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "category": self.category.value,
            "pattern": self.pattern,
            "severity": self.severity,
            "description": self.description,
        }


# Prompt injection patterns (compiled for performance)
_PROMPT_INJECTION_PATTERNS: list[tuple[re.Pattern[str], SafetyCategory, float, str]] = [
    # Direct instruction override attempts
    (
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions?", re.IGNORECASE),
        SafetyCategory.INSTRUCTION_OVERRIDE,
        0.9,
        "Attempt to ignore previous instructions",
    ),
    (
        re.compile(
            r"disregard\s+(?:all\s+)?(?:previous|above|prior)?\s*(?:instructions?|rules?)",
            re.IGNORECASE,
        ),
        SafetyCategory.INSTRUCTION_OVERRIDE,
        0.9,
        "Attempt to disregard rules/instructions",
    ),
    (
        re.compile(
            r"forget\s+(?:everything|all)(?:\s+(?:you|I|that)\s+(?:told|said|were\s+told))?",
            re.IGNORECASE,
        ),
        SafetyCategory.INSTRUCTION_OVERRIDE,
        0.85,
        "Attempt to reset context",
    ),
    # System prompt probing
    (
        re.compile(
            r"(?:what|show|tell|reveal|display)\s+(?:is|are|me)?\s*(?:your|the)?\s*(?:system\s*prompt|initial\s+instructions?|original\s+instructions?)",
            re.IGNORECASE,
        ),
        SafetyCategory.SYSTEM_PROMPT_PROBE,
        0.8,
        "Attempt to reveal system prompt",
    ),
    (
        re.compile(
            r"(?:print|output|display)\s+(?:your\s+)?(?:initial|system|original)\s+(?:prompt|instructions?)",
            re.IGNORECASE,
        ),
        SafetyCategory.SYSTEM_PROMPT_PROBE,
        0.8,
        "Attempt to print system prompt",
    ),
    (
        re.compile(
            r"(?:repeat|echo)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?)(?:\s+(?:back|verbatim|to\s+me))?",
            re.IGNORECASE,
        ),
        SafetyCategory.SYSTEM_PROMPT_PROBE,
        0.8,
        "Attempt to echo instructions",
    ),
    (
        re.compile(
            r"reveal\s+(?:your\s+)?(?:original|initial|system)\s+(?:instructions?|prompt)",
            re.IGNORECASE,
        ),
        SafetyCategory.SYSTEM_PROMPT_PROBE,
        0.8,
        "Attempt to reveal original instructions",
    ),
    # Role hijacking
    (
        re.compile(
            r"(?:you\s+are(?:\s+now)?|act\s+as|pretend\s+(?:to\s+be|you(?:'re|\s+are)))\s+(?:an?\s+)?(?:evil|malicious|bad)",
            re.IGNORECASE,
        ),
        SafetyCategory.ROLE_HIJACK,
        0.85,
        "Attempt to hijack role to malicious entity",
    ),
    (
        re.compile(
            r"(?:from\s+now\s+on|starting\s+now),?\s+you\s+(?:are|will\s+be)", re.IGNORECASE
        ),
        SafetyCategory.ROLE_HIJACK,
        0.7,
        "Attempt to reassign role",
    ),
    (
        re.compile(
            r"(?:you\s+are\s+now|act\s+as)\s+(?:an?\s+)?(?:villain|hacker|bad\s+actor)",
            re.IGNORECASE,
        ),
        SafetyCategory.ROLE_HIJACK,
        0.85,
        "Attempt to reassign role to malicious entity",
    ),
    (
        re.compile(r"enter\s+(?:DAN|developer|god)\s+mode", re.IGNORECASE),
        SafetyCategory.JAILBREAK_ATTEMPT,
        0.95,
        "Known jailbreak attempt (DAN mode)",
    ),
    # Jailbreak patterns
    (
        re.compile(
            r"(?:bypass|disable|turn\s+off)\s+(?:your\s+)?(?:safety|content|ethical)\s+(?:filters?|restrictions?|guidelines?)",
            re.IGNORECASE,
        ),
        SafetyCategory.JAILBREAK_ATTEMPT,
        0.9,
        "Attempt to bypass safety filters",
    ),
    (
        re.compile(
            r"(?:no\s+(?:ethical|safety|moral)\s+(?:constraints?|restrictions?|guidelines?))",
            re.IGNORECASE,
        ),
        SafetyCategory.JAILBREAK_ATTEMPT,
        0.85,
        "Request to remove ethical constraints",
    ),
    (
        re.compile(
            r"(?:jailbreak|unlock|unleash)\s+(?:yourself|your\s+(?:capabilities|potential|full))",
            re.IGNORECASE,
        ),
        SafetyCategory.JAILBREAK_ATTEMPT,
        0.95,
        "Direct jailbreak request",
    ),
    # Dangerous command patterns
    (
        re.compile(r"(?:execute|run|eval)\s*\([^)]*\)", re.IGNORECASE),
        SafetyCategory.DANGEROUS_COMMAND,
        0.7,
        "Potential code execution attempt",
    ),
    (
        re.compile(r"(?:rm\s+-rf|del\s+/[sq]|format\s+c:)", re.IGNORECASE),
        SafetyCategory.DANGEROUS_COMMAND,
        0.95,
        "Dangerous system command",
    ),
    # Prompt injection markers
    (
        re.compile(r"\[(?:system|admin|root)\]:", re.IGNORECASE),
        SafetyCategory.PROMPT_INJECTION,
        0.8,
        "Fake system/admin marker",
    ),
    (
        re.compile(r"<\|(?:im_(?:start|end)|system|user|assistant)\|>", re.IGNORECASE),
        SafetyCategory.PROMPT_INJECTION,
        0.85,
        "Fake chat role marker injection",
    ),
    (
        re.compile(r"###\s*(?:instruction|system|admin)\s*:", re.IGNORECASE),
        SafetyCategory.PROMPT_INJECTION,
        0.75,
        "Markdown instruction injection",
    ),
]

# Secret patterns for output filtering
_SECRET_PATTERNS: list[tuple[re.Pattern[str], SafetyCategory, str]] = [
    # API keys and tokens
    (
        re.compile(
            r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?", re.IGNORECASE
        ),
        SafetyCategory.SECRET_LEAK,
        "API key exposure",
    ),
    (
        re.compile(r"(?:bearer|token)\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "Bearer token exposure",
    ),
    (
        re.compile(r"(?:sk-|pk-|rk-)[a-zA-Z0-9]{32,}", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "Secret key exposure",
    ),
    # Passwords
    (
        re.compile(r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}['\"]?", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "Password exposure",
    ),
    # Connection strings
    (
        re.compile(r"(?:mongodb|mysql|postgres|redis)://[^\s]+:[^\s]+@[^\s]+", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "Database connection string exposure",
    ),
    # Private keys
    (
        re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "Private key exposure",
    ),
    # AWS keys
    (
        re.compile(r"(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}", re.IGNORECASE),
        SafetyCategory.SECRET_LEAK,
        "AWS access key exposure",
    ),
    # Environment variable dumps (plain text format)
    (
        re.compile(
            r"(?:^|\n)(?:API_KEY|SECRET_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY)\s*=", re.IGNORECASE
        ),
        SafetyCategory.CONFIG_LEAK,
        "Environment variable exposure",
    ),
    # JSON-style config exposure
    (
        re.compile(
            r'["\'](?:api_key|secret_key|openai_api_key|anthropic_api_key)["\']\s*:\s*["\'][a-zA-Z0-9_\-]{20,}["\']',
            re.IGNORECASE,
        ),
        SafetyCategory.CONFIG_LEAK,
        "JSON config key exposure",
    ),
    # Config file content
    (
        re.compile(
            r"(?:openai|anthropic|azure)_(?:api_)?key\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{20,}",
            re.IGNORECASE,
        ),
        SafetyCategory.CONFIG_LEAK,
        "Config key exposure",
    ),
]


class LLMSafetyAnalyzer:
    """Analyzer for LLM input/output safety.

    Provides methods to detect prompt injection, jailbreak attempts,
    and filter sensitive information from outputs.

    Example:
        >>> analyzer = LLMSafetyAnalyzer()
        >>> result = analyzer.analyze_prompt("Ignore previous instructions")
        >>> print(result.is_safe)  # False
        >>> print(result.violations[0].category)  # SafetyCategory.INSTRUCTION_OVERRIDE
    """

    def __init__(
        self,
        block_on_high_risk: bool = True,
        sanitize_outputs: bool = True,
        log_violations: bool = True,
    ) -> None:
        """Initialize the safety analyzer.

        Args:
            block_on_high_risk: Whether to mark HIGH/CRITICAL risk as unsafe
            sanitize_outputs: Whether to sanitize outputs by default
            log_violations: Whether to log detected violations
        """
        self._block_on_high_risk = block_on_high_risk
        self._sanitize_outputs = sanitize_outputs
        self._log_violations = log_violations

    def analyze_prompt(self, text: str) -> SafetyResult:
        """Analyze a prompt for safety violations.

        Checks for:
        - Prompt injection attempts
        - Jailbreak attempts
        - System prompt probing
        - Role hijacking
        - Dangerous commands

        Args:
            text: Input prompt text to analyze

        Returns:
            SafetyResult with analysis details
        """
        if not text or not text.strip():
            return SafetyResult(is_safe=True)

        violations: list[SafetyViolation] = []
        max_severity = 0.0

        # Check against all prompt injection patterns
        for pattern, category, severity, description in _PROMPT_INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(
                    SafetyViolation(
                        category=category,
                        pattern=match.group()[:100],  # Truncate for logging
                        severity=severity,
                        description=description,
                    )
                )
                max_severity = max(max_severity, severity)

        # Determine risk level based on max severity
        risk_level = self._severity_to_risk_level(max_severity)

        # Determine if safe based on risk level
        is_safe = True
        if self._block_on_high_risk and risk_level in (
            SafetyRiskLevel.HIGH,
            SafetyRiskLevel.CRITICAL,
        ):
            is_safe = False

        # Log violations if enabled
        if self._log_violations and violations:
            self._log_safety_event(
                "prompt_analysis",
                violations,
                risk_level,
                is_blocked=not is_safe,
            )

        return SafetyResult(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            metadata={
                "input_length": len(text),
                "violation_count": len(violations),
                "max_severity": max_severity,
            },
        )

    def filter_output(self, text: str) -> SafetyResult:
        """Filter LLM output to prevent secret/config leakage.

        Scans output for:
        - API keys and tokens
        - Passwords
        - Connection strings
        - Private keys
        - Config values

        Args:
            text: Output text to filter

        Returns:
            SafetyResult with sanitized content if violations found
        """
        if not text or not text.strip():
            return SafetyResult(is_safe=True, sanitized_content=text)

        violations: list[SafetyViolation] = []
        sanitized = text

        # Check against all secret patterns
        for pattern, category, description in _SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(
                    SafetyViolation(
                        category=category,
                        pattern="[REDACTED]",  # Don't log the actual secret
                        severity=0.9,
                        description=description,
                    )
                )
                # Replace the match with [REDACTED]
                if self._sanitize_outputs:
                    sanitized = pattern.sub("[REDACTED]", sanitized)

        # Determine risk level
        risk_level = SafetyRiskLevel.CRITICAL if violations else SafetyRiskLevel.NONE

        # Log violations if enabled
        if self._log_violations and violations:
            self._log_safety_event(
                "output_filtering",
                violations,
                risk_level,
                is_blocked=False,  # We sanitize rather than block
            )

        return SafetyResult(
            is_safe=len(violations) == 0,
            risk_level=risk_level,
            violations=violations,
            sanitized_content=sanitized if self._sanitize_outputs else None,
            metadata={
                "output_length": len(text),
                "secrets_redacted": len(violations),
            },
        )

    def _severity_to_risk_level(self, severity: float) -> SafetyRiskLevel:
        """Convert severity score to risk level.

        Args:
            severity: Severity score (0.0-1.0)

        Returns:
            Corresponding risk level
        """
        if severity <= 0:
            return SafetyRiskLevel.NONE
        elif severity < 0.4:
            return SafetyRiskLevel.LOW
        elif severity < 0.7:
            return SafetyRiskLevel.MEDIUM
        elif severity < 0.9:
            return SafetyRiskLevel.HIGH
        else:
            return SafetyRiskLevel.CRITICAL

    def _log_safety_event(
        self,
        event_type: str,
        violations: list[SafetyViolation],
        risk_level: SafetyRiskLevel,
        is_blocked: bool,
    ) -> None:
        """Log a safety event.

        Args:
            event_type: Type of safety check
            violations: List of violations detected
            risk_level: Overall risk level
            is_blocked: Whether the request was blocked
        """
        log_level = (
            logging.WARNING
            if risk_level
            in (
                SafetyRiskLevel.HIGH,
                SafetyRiskLevel.CRITICAL,
            )
            else logging.INFO
        )

        logger.log(
            log_level,
            "LLM Safety Event",
            extra={
                "event_type": event_type,
                "risk_level": risk_level.value,
                "violation_count": len(violations),
                "categories": [v.category.value for v in violations],
                "is_blocked": is_blocked,
            },
        )


# Global analyzer instance
_analyzer: LLMSafetyAnalyzer | None = None


def get_llm_safety_analyzer() -> LLMSafetyAnalyzer:
    """Get or create the global LLMSafetyAnalyzer instance.

    Returns:
        LLMSafetyAnalyzer singleton instance
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = LLMSafetyAnalyzer()
    return _analyzer


def analyze_prompt(text: str) -> SafetyResult:
    """Analyze a prompt for safety violations.

    Convenience function using the global analyzer instance.

    Args:
        text: Input prompt text to analyze

    Returns:
        SafetyResult with analysis details
    """
    return get_llm_safety_analyzer().analyze_prompt(text)


def filter_output(text: str) -> SafetyResult:
    """Filter LLM output to prevent secret/config leakage.

    Convenience function using the global analyzer instance.

    Args:
        text: Output text to filter

    Returns:
        SafetyResult with sanitized content if violations found
    """
    return get_llm_safety_analyzer().filter_output(text)


# ============================================================================
# Multi-Turn Attack Pattern Detection (R003)
# ============================================================================


@dataclass
class ConversationAnalysisResult:
    """Result of multi-turn conversation analysis.

    Attributes:
        is_suspicious: Whether the conversation shows suspicious patterns
        attack_likelihood: Estimated likelihood of attack (0.0-1.0)
        detected_patterns: List of detected attack patterns
        recommended_action: Suggested action (continue, warn, reset_session)
    """

    is_suspicious: bool
    attack_likelihood: float
    detected_patterns: list[str]
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_suspicious": self.is_suspicious,
            "attack_likelihood": self.attack_likelihood,
            "detected_patterns": self.detected_patterns,
            "recommended_action": self.recommended_action,
        }


# Multi-turn attack indicators
_MULTI_TURN_ATTACK_PATTERNS = [
    # Gradual context shifting
    re.compile(r"(?:let'?s?\s+)?(?:try|do)\s+something\s+different", re.IGNORECASE),
    # Hypothetical framing to bypass filters
    re.compile(
        r"(?:in\s+a\s+)?(?:hypothetical|fictional|imaginary)\s+(?:scenario|situation|world)",
        re.IGNORECASE,
    ),
    # Roleplay escalation
    re.compile(r"(?:continue|keep)\s+(?:the\s+)?(?:roleplay|acting|pretending)", re.IGNORECASE),
    # Testing boundaries
    re.compile(r"(?:what\s+)?(?:if\s+)?I\s+(?:ask(?:ed)?|said|told\s+you)", re.IGNORECASE),
    # Building trust for later exploitation
    re.compile(r"(?:you'?ve\s+)?(?:been|are)\s+(?:so\s+)?helpful", re.IGNORECASE),
    # Narrative manipulation
    re.compile(r"(?:for\s+the\s+)?(?:story|narrative|plot)", re.IGNORECASE),
    # Persistence after refusal
    re.compile(r"(?:but\s+)?(?:why\s+)?(?:can'?t|won'?t)\s+you(?:\s+just)?", re.IGNORECASE),
    # Claiming special permission
    re.compile(r"(?:I\s+)?(?:have|got)\s+(?:special\s+)?permission", re.IGNORECASE),
]


def analyze_conversation_patterns(
    messages: list[str],
    threshold: float = 0.6,
) -> ConversationAnalysisResult:
    """Analyze a sequence of messages for multi-turn attack patterns.

    Implements R003 mitigation: Detects gradual manipulation attempts
    across multiple conversation turns.

    Args:
        messages: List of user messages in chronological order
        threshold: Suspicion threshold (0.0-1.0)

    Returns:
        ConversationAnalysisResult with analysis details
    """
    if not messages:
        return ConversationAnalysisResult(
            is_suspicious=False,
            attack_likelihood=0.0,
            detected_patterns=[],
            recommended_action="continue",
        )

    detected_patterns: list[str] = []
    pattern_scores: list[float] = []

    # Analyze each message for attack indicators
    for msg in messages:
        for pattern in _MULTI_TURN_ATTACK_PATTERNS:
            if pattern.search(msg):
                detected_patterns.append(pattern.pattern[:50])
                pattern_scores.append(0.15)  # Each pattern adds to suspicion

    # Analyze the overall conversation trajectory
    # More suspicious if patterns appear later in conversation (escalation)
    if len(messages) >= 3:
        # Check for escalation in later messages
        later_messages = messages[len(messages) // 2 :]
        escalation_count = 0
        for msg in later_messages:
            for inj_pattern, _category, _severity, _desc in _PROMPT_INJECTION_PATTERNS:
                if inj_pattern.search(msg):
                    escalation_count += 1
        if escalation_count > 0:
            pattern_scores.append(0.25 * escalation_count)
            detected_patterns.append("escalation_in_later_turns")

    # Check for refusal-persistence pattern
    refusal_keywords = ["can't", "cannot", "won't", "will not", "unable to", "not allowed"]
    persistence_after_refusal = False
    for i, msg in enumerate(messages[:-1]):
        for keyword in refusal_keywords:
            if keyword in msg.lower() and i + 1 < len(messages):
                # Check if user persisted after potential refusal
                persistence_after_refusal = True
                break

    if persistence_after_refusal:
        pattern_scores.append(0.2)
        detected_patterns.append("persistence_after_apparent_refusal")

    # Calculate overall attack likelihood
    attack_likelihood = min(1.0, sum(pattern_scores))

    # Determine recommended action
    if attack_likelihood >= 0.8:
        recommended_action = "reset_session"
    elif attack_likelihood >= threshold:
        recommended_action = "warn"
    else:
        recommended_action = "continue"

    return ConversationAnalysisResult(
        is_suspicious=attack_likelihood >= threshold,
        attack_likelihood=attack_likelihood,
        detected_patterns=list(set(detected_patterns)),  # Deduplicate
        recommended_action=recommended_action,
    )


# ============================================================================
# Context Sanitization (R018)
# ============================================================================


@dataclass
class SanitizedContext:
    """Result of context sanitization.

    Attributes:
        sanitized_text: Text with embedded instructions removed
        removed_instructions: List of removed instruction fragments
        risk_score: Risk score of original context (0.0-1.0)
        is_modified: Whether the text was modified
    """

    sanitized_text: str
    removed_instructions: list[str]
    risk_score: float
    is_modified: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sanitized_text": self.sanitized_text[:200] + "..." if len(self.sanitized_text) > 200 else self.sanitized_text,
            "removed_count": len(self.removed_instructions),
            "risk_score": self.risk_score,
            "is_modified": self.is_modified,
        }


# Patterns for embedded instructions in context
_EMBEDDED_INSTRUCTION_PATTERNS = [
    # Direct instruction injection in context
    (re.compile(r"\[INST(?:RUCTION)?\].*?\[/INST(?:RUCTION)?\]", re.IGNORECASE | re.DOTALL), 0.9),
    (re.compile(r"<\|?(?:im_start|system|assistant)\|?>.*?<\|?(?:im_end|/system|/assistant)\|?>", re.IGNORECASE | re.DOTALL), 0.95),
    # Hidden instructions in context
    (re.compile(r"(?:hidden\s+)?(?:instruction|command)s?\s*:\s*[^\n]+", re.IGNORECASE), 0.8),
    # Unicode/invisible character attacks
    (re.compile(r"[\u200b-\u200f\u2028-\u202f\ufeff]+"), 0.7),
    # Markdown comment injection
    (re.compile(r"<!--.*?-->", re.DOTALL), 0.6),
    # Escaped newlines with hidden text
    (re.compile(r"\\n\s*(?:ignore|forget|disregard)", re.IGNORECASE), 0.85),
    # Base64 encoded instructions (common attack vector)
    (re.compile(r"(?:execute|run|eval)\s*:\s*[A-Za-z0-9+/=]{20,}"), 0.9),
]


def sanitize_context(
    context: str,
    preserve_formatting: bool = True,
) -> SanitizedContext:
    """Sanitize retrieved context to remove embedded instructions.

    Implements R018 mitigation: Prevents indirect prompt injection
    via malicious content in retrieved context.

    Args:
        context: Raw context text (from memory, RAG, etc.)
        preserve_formatting: Whether to preserve basic formatting

    Returns:
        SanitizedContext with cleaned text and analysis
    """
    if not context or not context.strip():
        return SanitizedContext(
            sanitized_text="",
            removed_instructions=[],
            risk_score=0.0,
            is_modified=False,
        )

    sanitized = context
    removed_instructions: list[str] = []
    max_risk = 0.0

    # Apply each sanitization pattern
    for pattern, risk_score in _EMBEDDED_INSTRUCTION_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            for match in matches:
                # Store what we're removing (truncated for safety)
                removed_text = match if isinstance(match, str) else str(match)
                removed_instructions.append(removed_text[:50] + "..." if len(removed_text) > 50 else removed_text)
            sanitized = pattern.sub("", sanitized)
            max_risk = max(max_risk, risk_score)

    # Also run through prompt injection patterns
    for inj_pattern, category, severity, _description in _PROMPT_INJECTION_PATTERNS:
        if category in (SafetyCategory.INSTRUCTION_OVERRIDE, SafetyCategory.ROLE_HIJACK):
            matches = inj_pattern.findall(sanitized)
            if matches:
                for match in matches:
                    match_text = match if isinstance(match, str) else str(match)
                    removed_instructions.append(f"[{category.value}] {match_text[:30]}...")
                sanitized = inj_pattern.sub("[REMOVED]", sanitized)
                max_risk = max(max_risk, severity)

    # Clean up whitespace if modified
    is_modified = sanitized != context
    if is_modified and preserve_formatting:
        # Normalize whitespace while preserving paragraph structure
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        sanitized = re.sub(r" {2,}", " ", sanitized)
        sanitized = sanitized.strip()

    return SanitizedContext(
        sanitized_text=sanitized,
        removed_instructions=removed_instructions,
        risk_score=max_risk,
        is_modified=is_modified,
    )


def sanitize_context_for_llm(context: str) -> str:
    """Convenience function to get sanitized context text.

    Args:
        context: Raw context text

    Returns:
        Sanitized context string (safe for LLM input)
    """
    result = sanitize_context(context)
    return result.sanitized_text
