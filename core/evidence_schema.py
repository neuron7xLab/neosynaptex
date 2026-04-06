"""Evidence schema validation — pure Python, no Pydantic."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "EvidenceRecord",
    "REQUIRED_FIELDS",
    "record_from_dict",
    "record_to_dict",
    "validate_record",
]


@dataclass(frozen=True)
class EvidenceRecord:
    substrate: str
    metric: str
    value: float
    ci95_lo: float
    ci95_hi: float
    method: str
    timestamp: float
    git_sha: str


REQUIRED_FIELDS = (
    "substrate",
    "metric",
    "value",
    "ci95_lo",
    "ci95_hi",
    "method",
    "timestamp",
    "git_sha",
)


def validate_record(record: EvidenceRecord) -> tuple[bool, list[str]]:
    """Validate an EvidenceRecord. Returns (valid, errors)."""
    errors: list[str] = []

    if not record.substrate or not isinstance(record.substrate, str):
        errors.append("substrate must be non-empty string")
    if not record.metric or not isinstance(record.metric, str):
        errors.append("metric must be non-empty string")
    if not np.isfinite(record.value):
        errors.append(f"value must be finite, got {record.value}")
    if not np.isfinite(record.ci95_lo):
        errors.append(f"ci95_lo must be finite, got {record.ci95_lo}")
    if not np.isfinite(record.ci95_hi):
        errors.append(f"ci95_hi must be finite, got {record.ci95_hi}")
    if record.ci95_lo > record.ci95_hi:
        errors.append(f"ci95_lo ({record.ci95_lo}) > ci95_hi ({record.ci95_hi})")
    if not record.method:
        errors.append("method must be non-empty")
    if record.timestamp <= 0:
        errors.append(f"timestamp must be > 0, got {record.timestamp}")
    if not record.git_sha or len(record.git_sha) < 7:
        errors.append(f"git_sha must be >= 7 chars, got '{record.git_sha}'")

    return (len(errors) == 0, errors)


def record_from_dict(d: dict[str, Any]) -> EvidenceRecord:
    """Create EvidenceRecord from dict with defaults."""
    return EvidenceRecord(
        substrate=d.get("substrate", ""),
        metric=d.get("metric", ""),
        value=float(d.get("value", float("nan"))),
        ci95_lo=float(d.get("ci95_lo", float("nan"))),
        ci95_hi=float(d.get("ci95_hi", float("nan"))),
        method=d.get("method", ""),
        timestamp=float(d.get("timestamp", time.time())),
        git_sha=d.get("git_sha", ""),
    )


def record_to_dict(record: EvidenceRecord) -> dict[str, Any]:
    return {
        "substrate": record.substrate,
        "metric": record.metric,
        "value": record.value,
        "ci95_lo": record.ci95_lo,
        "ci95_hi": record.ci95_hi,
        "method": record.method,
        "timestamp": record.timestamp,
        "git_sha": record.git_sha,
    }
