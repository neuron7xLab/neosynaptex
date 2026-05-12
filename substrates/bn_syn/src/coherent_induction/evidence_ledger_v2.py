from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvidenceLedgerEntryV2:
    utc_timestamp: str
    run_id: str
    role_sequence_hash: str
    hypothesis_hash: str
    artifact_hash: str
    config_hash: str
    model_name: str
    prompt_hash: str
    drift_score: float
    quality_score: float
    falsifier_verdict: str
    safety_verdict: str
    final_verdict: str
    failure_reason: str
    reproducibility_command: str


def _h(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def make_entry(payload: dict[str, object]) -> EvidenceLedgerEntryV2:
    return EvidenceLedgerEntryV2(utc_timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), **payload)


def to_json(entry: EvidenceLedgerEntryV2) -> str:
    return json.dumps(asdict(entry), sort_keys=True)
