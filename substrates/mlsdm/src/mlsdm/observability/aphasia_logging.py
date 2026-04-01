"""
Aphasia Observability Module

This module provides structured logging and metrics capabilities for aphasia detection
and repair decisions made by the NeuroLangWrapper. It enables audit trails and
observability for the Aphasia-Broca detection path without altering response semantics.

Key features:
- Structured logging with only metadata (no content/PII)
- Prometheus metrics integration for monitoring
- Support for detect, repair, and skip decisions
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from mlsdm.observability.aphasia_metrics import get_aphasia_metrics_exporter

LOGGER_NAME = "mlsdm.aphasia"


@dataclass
class AphasiaLogEvent:
    """
    Structured event representing an aphasia detection/repair decision.

    Attributes:
        decision: The decision made - "skip", "detected_no_repair", or "repaired"
        is_aphasic: Whether aphasia was detected in the response
        severity: Aphasia severity score (0.0 to 1.0)
        flags: List of aphasia indicators (e.g., "short_sentences", "low_function_words")
        detect_enabled: Whether aphasia detection was enabled
        repair_enabled: Whether aphasia repair was enabled
        severity_threshold: Severity threshold for triggering repair
    """

    decision: str
    is_aphasic: bool
    severity: float
    flags: Sequence[str]
    detect_enabled: bool
    repair_enabled: bool
    severity_threshold: float


def get_logger() -> logging.Logger:
    """
    Get the aphasia logger instance.

    Returns:
        Logger configured for aphasia observability
    """
    return logging.getLogger(LOGGER_NAME)


def log_aphasia_event(event: AphasiaLogEvent, emit_metrics: bool = True) -> None:
    """
    Log an aphasia detection/repair event with structured information.

    This function logs aphasia decisions at INFO level with all relevant context
    and optionally emits Prometheus metrics. Only metadata is logged - no content
    or PII is included.

    Args:
        event: The aphasia event to log
        emit_metrics: Whether to also emit Prometheus metrics (default: True)
    """
    logger = get_logger()
    logger.info(
        "[APHASIA] decision=%s is_aphasic=%s severity=%.3f flags=%s "
        "detect_enabled=%s repair_enabled=%s severity_threshold=%.3f",
        event.decision,
        event.is_aphasic,
        event.severity,
        ",".join(event.flags),
        event.detect_enabled,
        event.repair_enabled,
        event.severity_threshold,
    )

    # Emit Prometheus metrics
    if emit_metrics:
        # Determine mode based on config
        if not event.detect_enabled:
            mode = "disabled"
        elif event.repair_enabled:
            mode = "full"
        else:
            mode = "monitor"

        # Determine if repair was applied
        repair_applied = event.decision == "repaired"

        metrics = get_aphasia_metrics_exporter()
        metrics.record_aphasia_event(
            mode=mode,
            is_aphasic=event.is_aphasic,
            repair_applied=repair_applied,
            severity=event.severity,
            flags=list(event.flags),
        )
