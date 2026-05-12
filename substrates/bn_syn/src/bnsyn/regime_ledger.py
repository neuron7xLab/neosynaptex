from __future__ import annotations

import hashlib
import logging
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

LOGGER = logging.getLogger("bnsyn.regime.ledger")


def _log(event: str, **kwargs: object) -> None:
    LOGGER.info(json.dumps({"event": event, **kwargs}, sort_keys=True))


@dataclass(slots=True)
class RegimeRunRecord:
    utc_timestamp: str
    input_hash: str
    config_hash: str
    gamma: float
    entropy: float
    velocity: float
    gate_signal: float
    rest_phase: bool
    gamma_fallback_used: bool
    weight_norm_before: float
    weight_norm_after: float
    status: str
    git_commit_sha: str


def _sha256_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def build_run_record(weights_before: np.ndarray, weights_after: np.ndarray, diagnostics: object, config: dict[str, object], git_commit_sha: str, status: str = "ok") -> RegimeRunRecord:
    input_hash = _sha256_json({"weights_before": np.asarray(weights_before).tolist()})
    config_hash = _sha256_json(config)
    before_norm = float(np.linalg.norm(weights_before))
    after_norm = float(np.linalg.norm(weights_after))
    return RegimeRunRecord(
        utc_timestamp=utc_now_iso(),
        input_hash=input_hash,
        config_hash=config_hash,
        gamma=float(diagnostics.gamma),
        entropy=float(diagnostics.entropy),
        velocity=float(diagnostics.velocity),
        gate_signal=float(diagnostics.gate_signal),
        rest_phase=bool(diagnostics.rest_phase),
        gamma_fallback_used=bool(diagnostics.gamma_fallback_used),
        weight_norm_before=before_norm,
        weight_norm_after=after_norm,
        status=status,
        git_commit_sha=git_commit_sha,
    )


def append_run_record_jsonl(path: str, record: RegimeRunRecord) -> None:
    if not record.utc_timestamp.endswith("Z"):
        raise ValueError("UTC timestamp required (must end with Z)")
    p = Path(path).resolve()
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), sort_keys=True) + "\n")
            f.flush()
        _log("ledger_append_ok", path=str(p), status=record.status)
    except OSError as exc:
        _log("ledger_append_failed", path=str(p), error=str(exc))
        raise RuntimeError(f"ledger write failed: {exc}") from exc
