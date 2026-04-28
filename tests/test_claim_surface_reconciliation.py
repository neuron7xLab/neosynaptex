"""Tests for tools/audit/claim_surface_reconciliation.py.

Numbered tests:
1.  Empty / clean fixture → RECONCILED, exit 0.
2.  VALIDATED entry without ``data_source.sha256`` → CRITICAL violation.
3.  VALIDATED entry without ``adapter_code_hash`` → CRITICAL violation.
4.  VALIDATED entry missing ``null_family_status`` → HIGH violation.
5.  VALIDATED entry missing ``rerun_command`` → HIGH violation.
6.  BN-Syn ledger entry with VALIDATED → CRITICAL ``BNSYN_OVERCLAIM``.
7.  README forbidden phrase → HIGH violation.
8.  README "N validated substrates" → HIGH violation
    ``README_VALIDATED_COUNT_INCONSISTENT_WITH_EMPTY_CORE``.
9.  C-004 with Layer != Conjectural → CRITICAL ``C004_LAYER_OVERCLAIM``.
10. Mycelium contract missing ``BLOCKED_BY_METHOD_DEFINITION`` →
    CRITICAL ``MYCELIUM_CONTRACT_OVERCLAIM``.
11. Deterministic repeated invocation produces identical JSON.
12. ``main`` exit code is 2 on contradictions, 0 on RECONCILED.
13. Report markdown contains every violation row.
14. ``RECONCILED`` markdown body when no contradictions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.audit.claim_surface_reconciliation import (  # noqa: E402
    Violation,
    build_report,
    collect_violations,
    main,
)

_GOOD_HASH = "0" * 64


def _write_clean_fixture(root: Path) -> None:
    """Build a minimum repo fixture that should produce RECONCILED."""
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "contracts").mkdir(parents=True, exist_ok=True)

    ledger = {
        "version": "1.0.0",
        "entries": {
            "kuramoto_dense": {
                "substrate": "kuramoto_dense",
                "status": "VALIDATED",
                "data_source": {"sha256": _GOOD_HASH},
                "adapter_code_hash": _GOOD_HASH,
                "null_family_status": "shuffle:passed",
                "rerun_command": "python -m experiments.lemma_1_verification",
                "claim_boundary_ref": "docs/CLAIM_BOUNDARY.md#claim-c-002",
            },
        },
    }
    (root / "evidence" / "gamma_ledger.json").write_text(
        json.dumps(ledger, indent=2), encoding="utf-8"
    )

    (root / "README.md").write_text(
        "# NeoSynaptex\n\nRegime-marker hypothesis under active test.\n",
        encoding="utf-8",
    )

    (root / "docs" / "CLAIM_BOUNDARY.md").write_text(
        "# Claim boundary\n\n"
        "### Claim C-001\n- **Layer:** Proved\n\n"
        "### Claim C-004\n"
        "- **Layer:** Conjectural\n"
        "- **Statement:** open empirical conjecture.\n",
        encoding="utf-8",
    )

    (root / "contracts" / "mycelium_pre_admission.py").write_text(
        '"""Mycelium pre-admission contract."""\nBLOCKED_BY_METHOD_DEFINITION = True\n',
        encoding="utf-8",
    )


def _write_ledger_only(root: Path, entries: dict[str, Any]) -> None:
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / "evidence" / "gamma_ledger.json").write_text(
        json.dumps({"version": "1.0.0", "entries": entries}, indent=2),
        encoding="utf-8",
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "CLAIM_BOUNDARY.md").write_text(
        "### Claim C-004\n- **Layer:** Conjectural\n",
        encoding="utf-8",
    )
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / "mycelium_pre_admission.py").write_text(
        "BLOCKED_BY_METHOD_DEFINITION = True\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("Regime marker.\n", encoding="utf-8")


# 1
def test_clean_fixture_reconciles(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    violations = collect_violations(tmp_path)
    assert violations == []


# 2
def test_validated_without_data_sha256(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    ledger_path = tmp_path / "evidence" / "gamma_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    data["entries"]["kuramoto_dense"]["data_source"]["sha256"] = None
    ledger_path.write_text(json.dumps(data), encoding="utf-8")

    violations = collect_violations(tmp_path)
    codes = {v.code for v in violations}
    assert "VALIDATED_WITHOUT_DATA_SHA256" in codes


# 3
def test_validated_without_adapter_code_hash(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    ledger_path = tmp_path / "evidence" / "gamma_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    data["entries"]["kuramoto_dense"]["adapter_code_hash"] = "see something else"
    ledger_path.write_text(json.dumps(data), encoding="utf-8")

    violations = collect_violations(tmp_path)
    assert any(v.code == "VALIDATED_WITHOUT_ADAPTER_CODE_HASH" for v in violations)


# 4
def test_validated_without_null_family_status(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    ledger_path = tmp_path / "evidence" / "gamma_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    del data["entries"]["kuramoto_dense"]["null_family_status"]
    ledger_path.write_text(json.dumps(data), encoding="utf-8")

    violations = collect_violations(tmp_path)
    assert any(v.code == "VALIDATED_WITHOUT_NULL_FAMILY_STATUS" for v in violations)


# 5
def test_validated_without_rerun_command(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    ledger_path = tmp_path / "evidence" / "gamma_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    del data["entries"]["kuramoto_dense"]["rerun_command"]
    ledger_path.write_text(json.dumps(data), encoding="utf-8")

    violations = collect_violations(tmp_path)
    assert any(v.code == "VALIDATED_WITHOUT_RERUN_COMMAND" for v in violations)


# 6
def test_bnsyn_overclaim(tmp_path: Path) -> None:
    _write_ledger_only(
        tmp_path,
        {
            "bnsyn": {
                "substrate": "bn_syn",
                "status": "VALIDATED",
                "data_source": {"sha256": _GOOD_HASH},
                "adapter_code_hash": _GOOD_HASH,
                "null_family_status": "x",
                "rerun_command": "y",
                "claim_boundary_ref": "z",
            }
        },
    )
    violations = collect_violations(tmp_path)
    codes = {v.code for v in violations}
    assert "BNSYN_OVERCLAIM" in codes
    bnsyn = next(v for v in violations if v.code == "BNSYN_OVERCLAIM")
    assert bnsyn.severity == "CRITICAL"


# 7
def test_readme_forbidden_phrase(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    (tmp_path / "README.md").write_text(
        "# title\n\nThis confirms the universal law of γ.\n",
        encoding="utf-8",
    )
    violations = collect_violations(tmp_path)
    codes = {v.code for v in violations}
    assert "FORBIDDEN_UNIVERSAL" in codes


# 8
def test_readme_validated_count_inconsistent(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    (tmp_path / "README.md").write_text(
        "# title\n\nMean across 6 validated substrates.\n",
        encoding="utf-8",
    )
    violations = collect_violations(tmp_path)
    assert any(v.code == "README_VALIDATED_COUNT_INCONSISTENT_WITH_EMPTY_CORE" for v in violations)


# 9
def test_c004_layer_overclaim(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    (tmp_path / "docs" / "CLAIM_BOUNDARY.md").write_text(
        "### Claim C-004\n- **Layer:** Empirical\n- statement\n",
        encoding="utf-8",
    )
    violations = collect_violations(tmp_path)
    assert any(v.code == "C004_LAYER_OVERCLAIM" for v in violations)


# 10
def test_mycelium_contract_overclaim(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    (tmp_path / "contracts" / "mycelium_pre_admission.py").write_text(
        '"""no gate marker present."""\n',
        encoding="utf-8",
    )
    violations = collect_violations(tmp_path)
    assert any(v.code == "MYCELIUM_CONTRACT_OVERCLAIM" for v in violations)


# 11
def test_deterministic_repeated_invocation(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    main(["--repo-root", str(tmp_path), "--json-out", str(out1)])
    main(["--repo-root", str(tmp_path), "--json-out", str(out2)])
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


# 12
def test_main_exit_codes(tmp_path: Path) -> None:
    _write_clean_fixture(tmp_path)
    rc_clean = main(["--repo-root", str(tmp_path), "--json-out", str(tmp_path / "j.json")])
    assert rc_clean == 0

    (tmp_path / "README.md").write_text("γ = 1 everywhere now.\n", encoding="utf-8")
    rc_dirty = main(["--repo-root", str(tmp_path), "--json-out", str(tmp_path / "j2.json")])
    assert rc_dirty == 2


# 13
def test_report_includes_all_violations(tmp_path: Path) -> None:
    violations = [
        Violation(
            code="EXAMPLE",
            severity="HIGH",
            surface="x.md",
            locator="x:1",
            message="msg one",
            proposed_action="do thing",
        ),
        Violation(
            code="EXAMPLE_TWO",
            severity="CRITICAL",
            surface="y.md",
            locator="y:2",
            message="msg two",
            proposed_action="do other thing",
        ),
    ]
    md = build_report(violations)
    assert "EXAMPLE" in md
    assert "EXAMPLE_TWO" in md
    assert "do thing" in md
    assert "do other thing" in md


# 14
def test_reconciled_report_body() -> None:
    md = build_report([])
    assert "RECONCILED" in md
    assert "No contradictions" in md


def test_module_runs_as_script(tmp_path: Path) -> None:
    """Sanity: ``python -m tools.audit.claim_surface_reconciliation`` works."""
    _write_clean_fixture(tmp_path)
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.audit.claim_surface_reconciliation",
            "--repo-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "RECONCILED"
