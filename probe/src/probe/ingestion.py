"""JSONL session ingestion — fail-closed validation.

Input schema (one session per line):

    {
      "session_id": "unique_id",
      "mode": "human_ai" | "llm_only",
      "turns": [
        {"role": "human" | "assistant", "content": "...", "token_count": int>0},
        ...
      ]
    }

Validation (every rejection logged; never silent):
  * ``session_id`` present, unique within dataset
  * ``mode`` in {"human_ai", "llm_only"}
  * ``turns`` is list, len >= MIN_TURNS
  * every turn has role in {"human","assistant"}, token_count > 0,
    non-empty content
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probe.dialogue_adapter import Turn
from probe.session import MIN_TURNS, ProbeSession

_VALID_MODES = frozenset({"human_ai", "llm_only"})
_VALID_ROLES = frozenset({"human", "assistant"})


class IngestionError(ValueError):
    """Raised by ingestion when a rejection log cannot be written."""


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    mode: str
    turns: tuple[Turn, ...]


@dataclass(frozen=True)
class IngestionReport:
    accepted: tuple[SessionRecord, ...]
    rejected: tuple[tuple[str, str], ...]  # (raw_line, reason)
    rejection_log_path: Path | None


def ingest_jsonl(
    source: Path | str | Iterable[str],
    *,
    rejection_log_path: Path | None = None,
    min_turns: int = MIN_TURNS,
) -> IngestionReport:
    """Parse and validate a JSONL session corpus.

    ``source`` may be a filesystem path (str or ``Path``) or any iterable
    of raw line strings. Rejected sessions are appended to
    ``rejection_log_path`` (if provided) as JSONL with fields
    ``{"line": ..., "reason": ...}``. Callers that pass ``None`` receive
    the rejected list only via the returned ``IngestionReport``.
    """
    lines = _as_lines(source)
    accepted: list[SessionRecord] = []
    rejected: list[tuple[str, str]] = []
    seen_ids: set[str] = set()

    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped.strip():
            continue
        try:
            record = _parse_line(stripped, seen_ids, min_turns=min_turns)
        except IngestionError as exc:
            rejected.append((stripped, str(exc)))
            continue
        accepted.append(record)
        seen_ids.add(record.session_id)

    if rejection_log_path is not None:
        _write_rejection_log(rejection_log_path, rejected)

    return IngestionReport(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        rejection_log_path=rejection_log_path,
    )


def build_session(
    record: SessionRecord,
    *,
    window: int = 16,
    seed: int = 7,
) -> ProbeSession:
    """Replay a ``SessionRecord`` through a fresh ``ProbeSession``."""
    session = ProbeSession(window=window, seed=seed)
    for turn in record.turns:
        session.push_turn(turn)
    return session


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------
def _parse_line(
    line: str,
    seen_ids: set[str],
    *,
    min_turns: int,
) -> SessionRecord:
    try:
        data: Any = json.loads(line)
    except json.JSONDecodeError as exc:
        raise IngestionError(f"invalid JSON: {exc.msg}") from None

    if not isinstance(data, dict):
        raise IngestionError("top-level JSON must be an object")

    session_id_val = data.get("session_id")
    if not isinstance(session_id_val, str) or not session_id_val:
        raise IngestionError("session_id missing or not a non-empty string")
    session_id: str = session_id_val
    if session_id in seen_ids:
        raise IngestionError(f"duplicate session_id: {session_id!r}")

    mode = data.get("mode")
    if mode not in _VALID_MODES:
        raise IngestionError(f"mode must be one of {sorted(_VALID_MODES)}, got {mode!r}")

    raw_turns = data.get("turns")
    if not isinstance(raw_turns, list):
        raise IngestionError("turns must be a list")
    if len(raw_turns) < min_turns:
        raise IngestionError(f"turns has {len(raw_turns)} entries, need >= {min_turns}")

    parsed: list[Turn] = []
    for idx, raw in enumerate(raw_turns):
        if not isinstance(raw, dict):
            raise IngestionError(f"turn[{idx}] must be an object")
        role = raw.get("role")
        if role not in _VALID_ROLES:
            raise IngestionError(
                f"turn[{idx}].role must be in {sorted(_VALID_ROLES)}, got {role!r}"
            )
        content = raw.get("content")
        if not isinstance(content, str) or not content:
            raise IngestionError(f"turn[{idx}].content missing or not a non-empty string")
        tc = raw.get("token_count")
        if not isinstance(tc, int) or isinstance(tc, bool) or tc <= 0:
            raise IngestionError(f"turn[{idx}].token_count must be a positive int, got {tc!r}")
        parsed.append(Turn(role=role, content=content, token_count=tc))

    return SessionRecord(session_id=session_id, mode=str(mode), turns=tuple(parsed))


def _as_lines(source: Path | str | Iterable[str]) -> Iterator[str]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        with path.open("r", encoding="utf-8") as fh:
            yield from fh
        return
    yield from source


def _write_rejection_log(path: Path, rejected: list[tuple[str, str]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as fh:
            for raw, reason in rejected:
                fh.write(json.dumps({"line": raw, "reason": reason}, sort_keys=True) + "\n")
    except OSError as exc:  # pragma: no cover - filesystem edge
        raise IngestionError(f"cannot write rejection log at {path}: {exc}") from exc
