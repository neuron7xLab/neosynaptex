"""Deterministic tests for the §VII Measurement-Contract Verifier."""

from __future__ import annotations

import pathlib
import textwrap

from tools.adversarial.verifier import (
    CONTRACT_SOURCES,
    REQUIRED_FIELDS,
    ContractVerdict,
    VerdictKind,
    VerifierReport,
    load_instrumented_contracts,
    run_check,
    verify_contract,
)

# ---------------------------------------------------------------------------
# REQUIRED_FIELDS — pin the canon
# ---------------------------------------------------------------------------


def test_required_fields_include_all_eight_per_measurement_contract_v1():
    expected = {
        "substrate",
        "signal",
        "method",
        "window",
        "controls",
        "fake_alternative",
        "falsifier",
        "interpretation_boundary",
    }
    assert set(REQUIRED_FIELDS) == expected
    assert len(REQUIRED_FIELDS) == 8, (
        "MEASUREMENT_CONTRACT.md §1 pins eight fields; "
        "changing this requires a §5/§6 PR to the canon"
    )


# ---------------------------------------------------------------------------
# verify_contract — unit-level verdict logic
# ---------------------------------------------------------------------------


def _full_contract(**overrides) -> dict:
    base = {
        "_signal_id": "test_signal",
        "_source": "docs/synthetic.md",
        "substrate": "git repo",
        "signal": "per-commit label count",
        "method": "tools.audit.claim_status_applied.run_audit",
        "window": "rolling 30-day, 3 windows",
        "controls": "normalise by commits/window; exclude self-refs",
        "fake_alternative": "ritual label-pasting caught by diversity gate",
        "falsifier": "3 consecutive windows with zero labelled blocks",
        "interpretation_boundary": ("measures application discipline, not semantic correctness"),
    }
    base.update(overrides)
    return base


def test_verify_contract_ok_on_full_contract():
    v = verify_contract(_full_contract())
    assert v.kind == VerdictKind.OK
    assert v.ok
    assert v.missing == ()
    assert v.malformed == ()


def test_verify_contract_flags_missing_interpretation_boundary():
    c = _full_contract()
    del c["interpretation_boundary"]
    v = verify_contract(c)
    assert v.kind == VerdictKind.INCOMPLETE
    assert "interpretation_boundary" in v.missing


def test_verify_contract_flags_empty_string_as_missing():
    c = _full_contract(signal="   ")
    v = verify_contract(c)
    assert v.kind == VerdictKind.INCOMPLETE
    assert "signal" in v.missing


def test_verify_contract_accepts_fake_alternative_guard_alias():
    c = _full_contract()
    # Rename fake_alternative → fake_alternative_guard (existing repo
    # terminology). Verifier must accept the alias.
    c["fake_alternative_guard"] = c.pop("fake_alternative")
    v = verify_contract(c)
    assert v.kind == VerdictKind.OK


def test_verify_contract_flags_malformed_method_without_dotted_reference():
    c = _full_contract(method="todo")
    v = verify_contract(c)
    assert v.kind == VerdictKind.MALFORMED
    assert any("method" in m for m in v.malformed)


def test_verify_contract_flags_malformed_method_single_word():
    c = _full_contract(method="count_labels")  # no dot = no module reference
    v = verify_contract(c)
    assert v.kind == VerdictKind.MALFORMED


def test_verify_contract_accepts_method_with_module_class_function():
    c = _full_contract(method="tools.audit.foo.Bar.baz")
    v = verify_contract(c)
    assert v.kind == VerdictKind.OK


def test_verify_contract_missing_takes_precedence_over_malformed_when_isolated():
    # Only missing, no malformed ⇒ INCOMPLETE not MALFORMED
    c = _full_contract()
    del c["controls"]
    v = verify_contract(c)
    assert v.kind == VerdictKind.INCOMPLETE


def test_verify_contract_malformed_takes_precedence_when_both_present():
    # With both missing and malformed, MALFORMED dominates.
    c = _full_contract(method="x")  # malformed
    del c["controls"]  # missing
    v = verify_contract(c)
    assert v.kind == VerdictKind.MALFORMED


def test_verify_contract_empty_dict_is_incomplete_with_all_eight_missing():
    v = verify_contract({"_signal_id": "bare", "_source": "x"})
    assert v.kind == VerdictKind.INCOMPLETE
    assert set(v.missing) == set(REQUIRED_FIELDS)


def test_contract_verdict_as_str_ok():
    v = ContractVerdict(
        signal_id="sig",
        source="s.md",
        kind=VerdictKind.OK,
        missing=(),
        malformed=(),
    )
    assert "ok" in v.as_str()


def test_contract_verdict_as_str_failure_lists_both_missing_and_malformed():
    v = ContractVerdict(
        signal_id="sig",
        source="s.md",
        kind=VerdictKind.MALFORMED,
        missing=("window",),
        malformed=("method=..."),
    )
    s = v.as_str()
    assert "missing" in s
    assert "malformed" in s


# ---------------------------------------------------------------------------
# load_instrumented_contracts — integration with SYSTEM_PROTOCOL.md
# ---------------------------------------------------------------------------


def _write_system_protocol(tmp_path: pathlib.Path, frontmatter: str) -> pathlib.Path:
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    path = tmp_path / "docs" / "SYSTEM_PROTOCOL.md"
    body = "---\n" + frontmatter.strip() + "\n---\n\n# body\n"
    path.write_text(body, encoding="utf-8")
    return path


def test_load_instrumented_skips_not_instrumented_entries(tmp_path):
    _write_system_protocol(
        tmp_path,
        textwrap.dedent(
            """\
            version: v1.1
            kill_criteria:
              - id: instrumented_one
                measurement_status: instrumented
                signal_contract:
                  substrate: "git repo"
                  signal: "x"
                  method: "pkg.mod.fn"
                  window: "30-day"
                  controls: "norm"
                  fake_alternative: "pattern"
                  falsifier: "no labels 3x"
                  interpretation_boundary: "application, not correctness"
              - id: prose_only_one
                measurement_status: not_instrumented
            """
        ),
    )
    contracts = load_instrumented_contracts(
        sources=("docs/SYSTEM_PROTOCOL.md",), repo_root=tmp_path
    )
    ids = [c["_signal_id"] for c in contracts]
    assert ids == ["instrumented_one"]


def test_load_instrumented_empty_signal_contract_becomes_empty_dict(tmp_path):
    _write_system_protocol(
        tmp_path,
        textwrap.dedent(
            """\
            version: v1.1
            kill_criteria:
              - id: bare
                measurement_status: instrumented
            """
        ),
    )
    contracts = load_instrumented_contracts(
        sources=("docs/SYSTEM_PROTOCOL.md",), repo_root=tmp_path
    )
    assert len(contracts) == 1
    # A bare instrumented entry with no signal_contract is still
    # checked (and will come back INCOMPLETE with all 8 fields
    # missing).
    assert contracts[0]["_signal_id"] == "bare"


def test_load_instrumented_skips_source_file_that_does_not_exist(tmp_path):
    # Not a failure — just no contracts from a nonexistent source.
    contracts = load_instrumented_contracts(sources=("docs/nope.md",), repo_root=tmp_path)
    assert contracts == []


# ---------------------------------------------------------------------------
# run_check — end-to-end
# ---------------------------------------------------------------------------


def test_run_check_fails_when_any_contract_incomplete(tmp_path):
    _write_system_protocol(
        tmp_path,
        textwrap.dedent(
            """\
            version: v1.1
            kill_criteria:
              - id: bad
                measurement_status: instrumented
                signal_contract:
                  substrate: "x"
                  signal: "y"
                  method: "pkg.mod.fn"
                  window: "w"
                  controls: "c"
                  fake_alternative: "f"
                  falsifier: "F"
                  # interpretation_boundary intentionally missing
            """
        ),
    )
    code, report, summary = run_check(sources=("docs/SYSTEM_PROTOCOL.md",), repo_root=tmp_path)
    assert code == 2
    assert report.n_ok == 0
    assert "interpretation_boundary" in summary


def test_run_check_passes_with_all_contracts_complete(tmp_path):
    _write_system_protocol(
        tmp_path,
        textwrap.dedent(
            """\
            version: v1.1
            kill_criteria:
              - id: good
                measurement_status: instrumented
                signal_contract:
                  substrate: "x"
                  signal: "y"
                  method: "pkg.mod.fn"
                  window: "w"
                  controls: "c"
                  fake_alternative: "f"
                  falsifier: "F"
                  interpretation_boundary: "bounded"
            """
        ),
    )
    code, report, summary = run_check(sources=("docs/SYSTEM_PROTOCOL.md",), repo_root=tmp_path)
    assert code == 0, summary
    assert report.n_ok == 1
    assert report.ok


# ---------------------------------------------------------------------------
# Live repo invariant
# ---------------------------------------------------------------------------


def test_repo_canonical_state_passes_verifier():
    """Main MUST satisfy §VII for every instrumented kill-signal.

    If this fails: a PR landed an instrumented signal whose
    signal_contract is incomplete or malformed under
    MEASUREMENT_CONTRACT.md §1. Close the gap or revert the
    instrumentation.
    """

    code, report, summary = run_check()
    assert code == 0, summary


def test_contract_sources_points_at_real_files():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    for rel in CONTRACT_SOURCES:
        assert (repo_root / rel).is_file(), f"CONTRACT_SOURCES lists {rel} but file does not exist"


def test_verifier_report_counts_sum_to_total():
    r = VerifierReport(
        verdicts=(
            ContractVerdict("a", "x", VerdictKind.OK, (), ()),
            ContractVerdict("b", "x", VerdictKind.INCOMPLETE, ("substrate",), ()),
            ContractVerdict("c", "x", VerdictKind.MALFORMED, (), ("method",)),
        )
    )
    assert r.n_ok + r.n_incomplete + r.n_malformed == len(r.verdicts)
    assert not r.ok
