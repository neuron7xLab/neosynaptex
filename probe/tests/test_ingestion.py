"""JSONL ingestion tests — fail-closed validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.dialogue_adapter import Turn
from probe.ingestion import IngestionReport, SessionRecord, build_session, ingest_jsonl
from probe.session import MIN_TURNS


def _valid_turn_dict(n: int, seed_word: str = "hello") -> list[dict[str, object]]:
    return [
        {
            "role": "human" if i % 2 == 0 else "assistant",
            "content": f"{seed_word} turn {i} content words",
            "token_count": 20 + i,
        }
        for i in range(n)
    ]


def _valid_session_line(session_id: str, mode: str = "human_ai", n: int = MIN_TURNS) -> str:
    payload = {
        "session_id": session_id,
        "mode": mode,
        "turns": _valid_turn_dict(n),
    }
    return json.dumps(payload)


def test_valid_session_parsed() -> None:
    lines = [_valid_session_line("sess_1")]
    report = ingest_jsonl(iter(lines))
    assert isinstance(report, IngestionReport)
    assert len(report.accepted) == 1
    assert len(report.rejected) == 0
    record = report.accepted[0]
    assert isinstance(record, SessionRecord)
    assert record.session_id == "sess_1"
    assert record.mode == "human_ai"
    assert len(record.turns) == MIN_TURNS
    for t in record.turns:
        assert isinstance(t, Turn)


def test_invalid_token_count_rejected() -> None:
    payload = json.loads(_valid_session_line("sess_x"))
    payload["turns"][0]["token_count"] = 0
    lines = [json.dumps(payload)]
    report = ingest_jsonl(iter(lines))
    assert len(report.accepted) == 0
    assert len(report.rejected) == 1
    _raw, reason = report.rejected[0]
    assert "token_count" in reason


def test_short_session_rejected() -> None:
    payload = {
        "session_id": "short",
        "mode": "human_ai",
        "turns": _valid_turn_dict(MIN_TURNS - 1),
    }
    report = ingest_jsonl([json.dumps(payload)])
    assert len(report.accepted) == 0
    assert len(report.rejected) == 1
    assert "MIN_TURNS" in report.rejected[0][1] or ">=" in report.rejected[0][1]


def test_duplicate_id_rejected() -> None:
    line = _valid_session_line("dup")
    report = ingest_jsonl([line, line])
    assert len(report.accepted) == 1
    assert len(report.rejected) == 1
    assert "duplicate" in report.rejected[0][1]


def test_invalid_mode_rejected() -> None:
    payload = json.loads(_valid_session_line("sess_mode"))
    payload["mode"] = "weird_mode"
    report = ingest_jsonl([json.dumps(payload)])
    assert len(report.accepted) == 0
    assert "mode" in report.rejected[0][1]


def test_invalid_role_rejected() -> None:
    payload = json.loads(_valid_session_line("sess_role"))
    payload["turns"][2]["role"] = "system"
    report = ingest_jsonl([json.dumps(payload)])
    assert len(report.accepted) == 0
    assert "role" in report.rejected[0][1]


def test_malformed_json_rejected() -> None:
    lines = ["{not: json", _valid_session_line("ok")]
    report = ingest_jsonl(lines)
    assert len(report.accepted) == 1
    assert len(report.rejected) == 1
    assert "JSON" in report.rejected[0][1]


def test_rejected_written_to_log(tmp_path: Path) -> None:
    log = tmp_path / "rejected.jsonl"
    bad = json.dumps({"session_id": "bad", "mode": "human_ai", "turns": []})
    report = ingest_jsonl([bad], rejection_log_path=log)
    assert log.exists()
    content = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    entry = json.loads(content[0])
    assert "reason" in entry
    assert entry["line"] == bad
    assert report.rejection_log_path == log


def test_rejected_never_silently_dropped() -> None:
    # If no log path is provided, rejected sessions still appear in the
    # returned report — there is no path where validation errors vanish.
    report = ingest_jsonl(["not json at all"])
    assert len(report.rejected) == 1


def test_file_path_ingestion(tmp_path: Path) -> None:
    src = tmp_path / "corpus.jsonl"
    src.write_text(
        _valid_session_line("a") + "\n" + _valid_session_line("b") + "\n",
        encoding="utf-8",
    )
    report = ingest_jsonl(src)
    assert len(report.accepted) == 2
    assert len(report.rejected) == 0


def test_build_session_replays_turns() -> None:
    record = ingest_jsonl([_valid_session_line("sess_1")]).accepted[0]
    session = build_session(record, window=16, seed=7)
    assert session.n_turns == len(record.turns)
    assert session.adapter.domain == "dialogue"


def test_file_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_jsonl(tmp_path / "does_not_exist.jsonl")
