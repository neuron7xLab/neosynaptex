from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts import scan_placeholders

ALLOWED_STATUSES = {"OPEN", "IN_PROGRESS", "CLOSED", "ACCEPTED_BY_DESIGN"}


def test_scan_placeholders_json_contract() -> None:
    findings = scan_placeholders.collect_findings()

    assert findings == sorted(
        findings, key=lambda item: (item.path, item.line, item.kind, item.signature)
    )
    assert all(item.path for item in findings)
    assert all(item.line > 0 for item in findings)
    assert all(item.kind in {"code", "docs", "script", "test"} for item in findings)


def test_registry_covers_all_scan_findings() -> None:
    registry_path = Path("docs/PLACEHOLDER_REGISTRY.md")
    registry_text = registry_path.read_text(encoding="utf-8")

    id_pattern = re.compile(r"^- ID: (PH-\d{4})$", re.MULTILINE)
    path_pattern = re.compile(r"^- Path: `([^`]+)`$", re.MULTILINE)
    status_pattern = re.compile(r"^- Status: ([A-Z_]+)$", re.MULTILINE)

    registry_ids = id_pattern.findall(registry_text)
    registry_paths = [
        entry.split(":", maxsplit=1)[0] for entry in path_pattern.findall(registry_text)
    ]
    registry_statuses = status_pattern.findall(registry_text)

    assert registry_ids
    assert len(set(registry_ids)) == len(registry_ids)
    assert len(registry_paths) == len(registry_ids)
    assert len(registry_statuses) == len(registry_ids)
    assert set(registry_statuses) <= ALLOWED_STATUSES

    findings = scan_placeholders.collect_findings()
    scan_paths = {item.path for item in findings}

    assert scan_paths <= set(registry_paths)

    open_like_paths = {
        path
        for path, status in zip(registry_paths, registry_statuses, strict=True)
        if status in {"OPEN", "IN_PROGRESS"}
    }
    assert open_like_paths <= scan_paths


def test_registry_closed_entries_include_evidence_ref() -> None:
    registry_path = Path("docs/PLACEHOLDER_REGISTRY.md")
    registry_text = registry_path.read_text(encoding="utf-8")

    entry_blocks = [
        match.group(0)
        for match in re.finditer(
            r"^- ID: PH-\d{4}$.*?(?=\n\n- ID: PH-\d{4}$|\Z)",
            registry_text,
            flags=re.MULTILINE | re.DOTALL,
        )
    ]
    assert entry_blocks

    for entry in entry_blocks:
        status_match = re.search(r"^- Status: ([A-Z_]+)$", entry, flags=re.MULTILINE)
        assert status_match is not None
        status = status_match.group(1)
        evidence_ref_match = re.search(r"^- evidence_ref: `([^`]+)`$", entry, flags=re.MULTILINE)

        if status == "CLOSED":
            assert evidence_ref_match is not None
        if status == "OPEN":
            fix_strategy_match = re.search(
                r"^- Fix Strategy: `([^`]+)`$", entry, flags=re.MULTILINE
            )
            test_strategy_match = re.search(
                r"^- Test Strategy: `([^`]+)`$", entry, flags=re.MULTILINE
            )
            assert fix_strategy_match is not None
            assert test_strategy_match is not None


def test_scan_python_detects_not_implemented_variants_and_script_kind(tmp_path: Path) -> None:
    scan_root = tmp_path / "repo"
    script_file = scan_root / "scripts" / "sample.py"
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text(
        "import builtins\n"
        "def f():\n"
        "    raise NotImplementedError\n"
        "def g():\n"
        "    raise NotImplementedError()\n"
        "def h():\n"
        "    raise builtins.NotImplementedError()\n",
        encoding="utf-8",
    )

    original_root = scan_placeholders.ROOT
    original_targets = scan_placeholders.TARGET_DIRS
    try:
        scan_placeholders.ROOT = scan_root
        scan_placeholders.TARGET_DIRS = ("scripts",)
        findings = scan_placeholders.collect_findings()
    finally:
        scan_placeholders.ROOT = original_root
        scan_placeholders.TARGET_DIRS = original_targets

    assert len(findings) == 3
    assert all(item.path == "scripts/sample.py" for item in findings)
    assert all(item.kind == "script" for item in findings)
    assert all(item.signature == "raise_NotImplementedError" for item in findings)
    assert [item.line for item in findings] == [3, 5, 7]


def test_scan_placeholders_cli_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["scan_placeholders", "--format", "json"])
    exit_code = scan_placeholders.main()
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert isinstance(payload, list)


def test_placeholder_scan_and_registry_have_no_open_entries() -> None:
    findings = scan_placeholders.collect_findings()
    assert findings == []

    registry_path = Path("docs/PLACEHOLDER_REGISTRY.md")
    registry_text = registry_path.read_text(encoding="utf-8")
    status_pattern = re.compile(r"^- Status: ([A-Z_]+)$", re.MULTILINE)
    statuses = status_pattern.findall(registry_text)

    assert statuses
    assert all(status not in {"OPEN", "IN_PROGRESS"} for status in statuses)


def test_scan_python_detects_todo_fixme_markers_outside_tests(tmp_path: Path) -> None:
    scan_root = tmp_path / "repo"
    script_file = scan_root / "scripts" / "sample.py"
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text(
        "def f():\n"
        "    # TODO: implement branch\n"
        "    return 1\n"
        "\n"
        "# FIXME: remove fallback\n",
        encoding="utf-8",
    )

    original_root = scan_placeholders.ROOT
    original_targets = scan_placeholders.TARGET_DIRS
    try:
        scan_placeholders.ROOT = scan_root
        scan_placeholders.TARGET_DIRS = ("scripts",)
        findings = scan_placeholders.collect_findings()
    finally:
        scan_placeholders.ROOT = original_root
        scan_placeholders.TARGET_DIRS = original_targets

    assert [item.signature for item in findings] == ["todo_fixme_marker", "todo_fixme_marker"]
    assert [item.line for item in findings] == [2, 5]
    assert all(item.kind == "script" for item in findings)


def test_scan_python_ignores_todo_fixme_markers_in_tests(tmp_path: Path) -> None:
    scan_root = tmp_path / "repo"
    test_file = scan_root / "tests" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "def test_x():\n"
        "    # TODO: assertion later\n"
        "    assert True\n",
        encoding="utf-8",
    )

    original_root = scan_placeholders.ROOT
    original_targets = scan_placeholders.TARGET_DIRS
    try:
        scan_placeholders.ROOT = scan_root
        scan_placeholders.TARGET_DIRS = ("tests",)
        findings = scan_placeholders.collect_findings()
    finally:
        scan_placeholders.ROOT = original_root
        scan_placeholders.TARGET_DIRS = original_targets

    assert findings == []
