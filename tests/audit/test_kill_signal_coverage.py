"""Deterministic tests for the kill-signal coverage ratchet.

The tool exposes three seams: ``load_kill_criteria`` (frontmatter
parse), ``load_baseline`` (JSON parse), and ``run_check`` (the
integrity-plus-ratchet verdict). Tests exercise each directly and
also assert the live repo satisfies the invariant today.
"""

from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

from tools.audit.kill_signal_coverage import (
    IntegrityError,
    load_baseline,
    load_kill_criteria,
    run_check,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_PROTOCOL_FRONTMATTER_TEMPLATE = """---
version: v1.1
kill_criteria:
{criteria}
---

# body
"""


def _write_protocol(tmp_path: pathlib.Path, criteria_yaml: str) -> pathlib.Path:
    """Write a synthetic SYSTEM_PROTOCOL.md with the given kill_criteria block."""

    content = _PROTOCOL_FRONTMATTER_TEMPLATE.format(
        criteria=textwrap.indent(criteria_yaml.rstrip(), "  ")
    )
    path = tmp_path / "SYSTEM_PROTOCOL.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_baseline(tmp_path: pathlib.Path, value: int) -> pathlib.Path:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"min_instrumented_count": value}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_kill_criteria — frontmatter parsing
# ---------------------------------------------------------------------------


def test_load_kill_criteria_reads_instrumented_and_not_instrumented(tmp_path):
    yaml_block = textwrap.dedent(
        """\
        - id: taxonomy_disuse
          statement: labels stop being applied
          measurement_status: instrumented
          signal_contract:
            tool: tools/audit/claim_status_applied.py
            test_suite: tests/audit/test_claim_status_applied.py
        - id: wrong_bottlenecks
          statement: responses identify wrong bottlenecks
          measurement_status: not_instrumented
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    criteria = load_kill_criteria(protocol)

    assert [c["id"] for c in criteria] == ["taxonomy_disuse", "wrong_bottlenecks"]
    assert criteria[0]["measurement_status"] == "instrumented"
    assert criteria[0]["signal_contract"]["tool"] == ("tools/audit/claim_status_applied.py")
    assert criteria[1]["measurement_status"] == "not_instrumented"


def test_load_kill_criteria_rejects_missing_frontmatter(tmp_path):
    path = tmp_path / "no_frontmatter.md"
    path.write_text("# just body\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="frontmatter"):
        load_kill_criteria(path)


def test_load_kill_criteria_rejects_missing_list(tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("---\nversion: v1\n---\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="kill_criteria"):
        load_kill_criteria(path)


# ---------------------------------------------------------------------------
# load_baseline
# ---------------------------------------------------------------------------


def test_load_baseline_returns_int(tmp_path):
    path = _write_baseline(tmp_path, 3)
    assert load_baseline(path) == 3


def test_load_baseline_rejects_missing(tmp_path):
    with pytest.raises(IntegrityError, match="baseline file not found"):
        load_baseline(tmp_path / "does_not_exist.json")


def test_load_baseline_rejects_non_int(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"min_instrumented_count": "three"}), encoding="utf-8")
    with pytest.raises(IntegrityError, match="non-negative int"):
        load_baseline(path)


def test_load_baseline_rejects_negative(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"min_instrumented_count": -1}), encoding="utf-8")
    with pytest.raises(IntegrityError, match="non-negative int"):
        load_baseline(path)


# ---------------------------------------------------------------------------
# run_check — integrity + ratchet
# ---------------------------------------------------------------------------


def test_run_check_passes_when_contracts_exist_and_count_at_baseline(tmp_path):
    tool = tmp_path / "tools/audit/my_tool.py"
    test = tmp_path / "tests/audit/test_my_tool.py"
    for p in (tool, test):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# exists\n", encoding="utf-8")

    yaml_block = textwrap.dedent(
        """\
        - id: ks1
          statement: signal one
          measurement_status: instrumented
          signal_contract:
            tool: tools/audit/my_tool.py
            test_suite: tests/audit/test_my_tool.py
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    baseline = _write_baseline(tmp_path, 1)

    code, msg = run_check(system_protocol=protocol, baseline_path=baseline, repo_root=tmp_path)
    assert code == 0, msg
    assert "1/1 kill-signals instrumented" in msg


def test_run_check_fails_when_instrumented_tool_missing(tmp_path):
    yaml_block = textwrap.dedent(
        """\
        - id: ks1
          statement: signal one
          measurement_status: instrumented
          signal_contract:
            tool: tools/audit/nonexistent.py
            test_suite: tests/audit/nonexistent.py
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    baseline = _write_baseline(tmp_path, 0)

    code, msg = run_check(system_protocol=protocol, baseline_path=baseline, repo_root=tmp_path)
    assert code == 2
    assert "missing path" in msg
    assert "ks1" in msg


def test_run_check_fails_on_instrumented_without_signal_contract(tmp_path):
    yaml_block = textwrap.dedent(
        """\
        - id: ks_bare
          statement: no contract
          measurement_status: instrumented
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    baseline = _write_baseline(tmp_path, 0)

    code, msg = run_check(system_protocol=protocol, baseline_path=baseline, repo_root=tmp_path)
    assert code == 2
    # The parser may represent a missing signal_contract as absent OR empty;
    # either way the verdict is DRIFT with a reference to the entry.
    assert "DRIFT" in msg
    assert "ks_bare" in msg


def test_run_check_fails_when_count_below_baseline(tmp_path):
    tool = tmp_path / "tools/audit/only.py"
    test = tmp_path / "tests/audit/test_only.py"
    for p in (tool, test):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# exists\n", encoding="utf-8")

    yaml_block = textwrap.dedent(
        """\
        - id: ks_only
          statement: only one
          measurement_status: instrumented
          signal_contract:
            tool: tools/audit/only.py
            test_suite: tests/audit/test_only.py
        - id: regressed
          statement: previously instrumented, now prose-only
          measurement_status: not_instrumented
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    baseline = _write_baseline(tmp_path, 2)

    code, msg = run_check(system_protocol=protocol, baseline_path=baseline, repo_root=tmp_path)
    assert code == 2
    assert "regressed" in msg
    assert "baseline=2" in msg
    assert "current=1" in msg


def test_run_check_ignores_not_instrumented_contract_integrity(tmp_path):
    """A not_instrumented entry is allowed to have no signal_contract."""

    tool = tmp_path / "tools/audit/the_one.py"
    test = tmp_path / "tests/audit/test_the_one.py"
    for p in (tool, test):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# exists\n", encoding="utf-8")

    yaml_block = textwrap.dedent(
        """\
        - id: ks_instr
          statement: instrumented
          measurement_status: instrumented
          signal_contract:
            tool: tools/audit/the_one.py
            test_suite: tests/audit/test_the_one.py
        - id: ks_prose
          statement: prose only
          measurement_status: not_instrumented
        """
    )
    protocol = _write_protocol(tmp_path, yaml_block)
    baseline = _write_baseline(tmp_path, 1)

    code, msg = run_check(system_protocol=protocol, baseline_path=baseline, repo_root=tmp_path)
    assert code == 0, msg


# ---------------------------------------------------------------------------
# Live repo invariant
# ---------------------------------------------------------------------------


def test_repo_canonical_state_passes_ratchet():
    """HEAD MUST satisfy the kill-signal coverage ratchet.

    If this fails: either SYSTEM_PROTOCOL.md declared a new
    instrumented entry whose tool/test paths do not exist, or a
    previously instrumented entry was demoted to not_instrumented
    without bumping kill_signal_baseline.json in the same diff.
    """

    code, msg = run_check()
    assert code == 0, msg
