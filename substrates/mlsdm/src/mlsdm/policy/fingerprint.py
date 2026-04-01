"""Policy Fingerprint System for Drift Detection (TD-002).

This module implements the canonical fingerprint algorithm for detecting
policy drift in safety-critical thresholds. It provides:

1. Canonical serialization of policy thresholds
2. SHA-256 fingerprinting for tamper detection
3. Structured JSON logging for audit trails
4. Drift detection between fingerprint snapshots

Resolves: TD-002 (HIGH priority - Policy Drift Guard)

Section 10.1: Canonical fingerprint algorithm
- Serialize thresholds/policy to canonical JSON
- Sorted keys, stable float formatting, no whitespace
- Hash with SHA-256

Section 10.2: Structured logging format (JSON required)
- Emit POLICY_FINGERPRINT event with required fields

Section 10.3: Drift detection test
- Compute fingerprint A on baseline thresholds
- Modify threshold → fingerprint B
- Assert A != B and drift guard triggers
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from mlsdm.policy.exceptions import PolicyDriftError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyFingerprint:
    """Immutable policy fingerprint for drift detection.

    Attributes:
        fingerprint_sha256: SHA-256 hash of canonical policy JSON
        policy_version: Semantic version of the policy
        source_of_truth: Path/module where policy thresholds are defined
        timestamp_utc: ISO8601 timestamp when fingerprint was computed
        canonical_json: The canonical JSON representation (for debugging)
    """

    fingerprint_sha256: str
    policy_version: str
    source_of_truth: str
    timestamp_utc: str
    canonical_json: str


def _format_float(value: float) -> str:
    """Format float with stable precision for canonical representation.

    Uses 6 decimal places for consistency across platforms.
    """
    return f"{value:.6f}"


def _serialize_value(value: Any) -> Any:
    """Recursively serialize values for canonical JSON."""
    if isinstance(value, float):
        # Use string representation for stable floats
        return _format_float(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def compute_canonical_json(thresholds: dict[str, Any]) -> str:
    """Compute canonical JSON representation of policy thresholds.

    Section 10.1: Canonical fingerprint algorithm
    - Sorted keys
    - Stable float formatting
    - No whitespace (compact separators)

    Args:
        thresholds: Dictionary of policy thresholds

    Returns:
        Canonical JSON string (sorted keys, no whitespace)
    """
    canonical = _serialize_value(thresholds)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_fingerprint_hash(canonical_json: str) -> str:
    """Compute SHA-256 hash of canonical JSON.

    Args:
        canonical_json: Canonical JSON string

    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_policy_fingerprint(
    thresholds: dict[str, Any],
    policy_version: str,
    source_of_truth: str,
) -> PolicyFingerprint:
    """Compute a policy fingerprint for the given thresholds.

    Args:
        thresholds: Dictionary of policy thresholds (e.g., moral filter params)
        policy_version: Semantic version of the policy (e.g., "1.2.0")
        source_of_truth: Path or module name where thresholds are defined

    Returns:
        PolicyFingerprint with SHA-256 hash and metadata
    """
    canonical_json = compute_canonical_json(thresholds)
    fingerprint_hash = compute_fingerprint_hash(canonical_json)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")

    return PolicyFingerprint(
        fingerprint_sha256=fingerprint_hash,
        policy_version=policy_version,
        source_of_truth=source_of_truth,
        timestamp_utc=timestamp,
        canonical_json=canonical_json,
    )


def emit_policy_fingerprint_event(fingerprint: PolicyFingerprint) -> dict[str, str]:
    """Emit structured JSON log for policy fingerprint event.

    Section 10.2: Structured logging format (JSON required)

    Emits event:
    {
        "event": "POLICY_FINGERPRINT",
        "fingerprint_sha256": "<hash>",
        "policy_version": "<semver>",
        "source_of_truth": "<path/module>",
        "timestamp_utc": "<iso8601>"
    }

    Args:
        fingerprint: PolicyFingerprint to log

    Returns:
        The structured event dictionary (for testing/verification)
    """
    event = {
        "event": "POLICY_FINGERPRINT",
        "fingerprint_sha256": fingerprint.fingerprint_sha256,
        "policy_version": fingerprint.policy_version,
        "source_of_truth": fingerprint.source_of_truth,
        "timestamp_utc": fingerprint.timestamp_utc,
    }

    # Log as structured JSON
    logger.info(json.dumps(event, sort_keys=True, separators=(",", ":")))

    return event


def detect_policy_drift(
    baseline: PolicyFingerprint,
    current: PolicyFingerprint,
) -> tuple[bool, str | None]:
    """Detect if policy has drifted from baseline.

    Section 10.3: Drift detection
    - Compare fingerprint hashes
    - Return True if drift detected

    Args:
        baseline: Baseline policy fingerprint
        current: Current policy fingerprint

    Returns:
        Tuple of (drift_detected, reason)
        - drift_detected: True if fingerprints differ
        - reason: Description of drift if detected, None otherwise
    """
    if baseline.fingerprint_sha256 != current.fingerprint_sha256:
        reason = (
            f"Policy drift detected: fingerprint changed from "
            f"{baseline.fingerprint_sha256[:16]}... to {current.fingerprint_sha256[:16]}... "
            f"(source: {current.source_of_truth})"
        )
        logger.warning(reason)
        return True, reason

    return False, None


class PolicyFingerprintGuard:
    """Guard that monitors policy fingerprints for drift.

    This class provides a stateful drift guard that:
    1. Computes fingerprints on policy load
    2. Emits structured events for audit trails
    3. Detects drift from baseline
    4. Raises on unauthorized changes

    Example:
        >>> guard = PolicyFingerprintGuard()
        >>> guard.register_baseline(
        ...     thresholds={"threshold": 0.5, "min": 0.3, "max": 0.9},
        ...     policy_version="1.2.0",
        ...     source_of_truth="src/mlsdm/cognition/moral_filter.py"
        ... )
        >>> # Later, check for drift
        >>> guard.check_drift(
        ...     thresholds={"threshold": 0.6, "min": 0.3, "max": 0.9},  # Changed!
        ...     policy_version="1.2.0",
        ...     source_of_truth="src/mlsdm/cognition/moral_filter.py"
        ... )
        PolicyDriftError: Policy drift detected...
    """

    def __init__(self) -> None:
        """Initialize the fingerprint guard."""
        self._baseline: PolicyFingerprint | None = None

    @property
    def baseline(self) -> PolicyFingerprint | None:
        """Get the current baseline fingerprint."""
        return self._baseline

    def register_baseline(
        self,
        thresholds: dict[str, Any],
        policy_version: str,
        source_of_truth: str,
    ) -> PolicyFingerprint:
        """Register a baseline fingerprint for drift detection.

        Args:
            thresholds: Policy thresholds dictionary
            policy_version: Semantic version
            source_of_truth: Path/module where thresholds are defined

        Returns:
            The computed baseline fingerprint
        """
        self._baseline = compute_policy_fingerprint(
            thresholds=thresholds,
            policy_version=policy_version,
            source_of_truth=source_of_truth,
        )
        emit_policy_fingerprint_event(self._baseline)
        return self._baseline

    def check_drift(
        self,
        thresholds: dict[str, Any],
        policy_version: str,
        source_of_truth: str,
        *,
        enforce: bool = True,
    ) -> tuple[bool, PolicyFingerprint]:
        """Check if current thresholds have drifted from baseline.

        Args:
            thresholds: Current policy thresholds
            policy_version: Current policy version
            source_of_truth: Current source of truth
            enforce: If True, raise PolicyDriftError on drift

        Returns:
            Tuple of (drift_detected, current_fingerprint)

        Raises:
            PolicyDriftError: If drift detected and enforce=True
            ValueError: If no baseline registered
        """
        if self._baseline is None:
            raise ValueError(
                "No baseline registered. Call register_baseline() first."
            )

        current = compute_policy_fingerprint(
            thresholds=thresholds,
            policy_version=policy_version,
            source_of_truth=source_of_truth,
        )
        emit_policy_fingerprint_event(current)

        drift_detected, reason = detect_policy_drift(self._baseline, current)

        if drift_detected and enforce:
            raise PolicyDriftError(reason or "Policy drift detected")

        return drift_detected, current

    def update_baseline(self, fingerprint: PolicyFingerprint) -> None:
        """Update the baseline to a new fingerprint.

        Use this after an authorized policy change has been approved.

        Args:
            fingerprint: New baseline fingerprint
        """
        self._baseline = fingerprint
        logger.info(
            "Baseline updated to fingerprint %s (policy version %s)",
            fingerprint.fingerprint_sha256[:16],
            fingerprint.policy_version,
        )
