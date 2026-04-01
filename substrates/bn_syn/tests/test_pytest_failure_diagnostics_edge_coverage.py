from __future__ import annotations

import sys
import types
import xml.etree.ElementTree as ET

import pytest

from bnsyn.proof.evaluate import evaluate_gate_g6_determinism
from bnsyn.qa import pytest_failure_diagnostics as diag


def test_safe_int_handles_invalid_and_none() -> None:
    assert diag._safe_int(None) == 0
    assert diag._safe_int("NaN") == 0


def test_ensure_redacted_fails_closed_on_redaction_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diag, "_redact_text", lambda _text: (_ for _ in ()).throw(RuntimeError("boom")))
    assert diag._ensure_redacted("secret") == "[REDACTION_ERROR]"


def test_parse_junit_xml_uses_defusedxml_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("defusedxml")
    module_et = types.SimpleNamespace(fromstring=lambda _text: ET.Element("testsuite", {"tests": "1"}))
    module.ElementTree = module_et
    monkeypatch.setitem(sys.modules, "defusedxml", module)

    root = diag._parse_junit_xml("<ignored />")
    assert root.tag == "testsuite"


def test_collect_suites_rejects_unknown_root() -> None:
    with pytest.raises(ValueError, match="Unsupported JUnit root element"):
        diag._collect_suites(ET.Element("unknown"))


def test_build_nodeid_fallback_variants() -> None:
    assert diag._build_nodeid("", "", "") == "<unknown_nodeid>"
    assert diag._build_nodeid("", "pkg.mod", "") == "pkg.mod"
    assert diag._build_nodeid("", "pkg.mod", "test_x") == "pkg/mod.py::test_x"
    assert diag._build_nodeid("tests/test_x.py", "", "") == "tests/test_x.py"


def test_extract_log_excerpt_returns_none_when_nodeid_absent() -> None:
    assert diag._extract_log_excerpt("no matching node", "tests/test_x.py::test_y") is None


def test_g6_determinism_fails_when_hashes_missing(tmp_path) -> None:
    (tmp_path / "robustness_report.json").write_text('{"replay_check": {"identical": true}}', encoding="utf-8")
    result = evaluate_gate_g6_determinism(tmp_path)
    assert result["status"] == "FAIL"
    assert result["details"] == "missing replay hashes"
