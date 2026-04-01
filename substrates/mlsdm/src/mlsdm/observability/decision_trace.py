from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DecisionTrace:
    """Structured decision trace for end-to-end explainability."""

    trace_id: str
    timestamp: str
    input: dict[str, Any]
    memory: dict[str, Any]
    prediction_error: dict[str, Any]
    neuromodulation: dict[str, Any]
    policy: dict[str, Any]
    action: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_decision_trace(
    *,
    input_payload: dict[str, Any],
    memory_payload: dict[str, Any],
    prediction_error: dict[str, Any],
    neuromodulation: dict[str, Any],
    policy: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    trace = DecisionTrace(
        trace_id=str(uuid.uuid4()),
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        input=input_payload,
        memory=memory_payload,
        prediction_error=prediction_error,
        neuromodulation=neuromodulation,
        policy=policy,
        action=action,
    )
    return trace.to_dict()
