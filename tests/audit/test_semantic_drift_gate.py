"""Deterministic tests for the semantic drift enforcement gate."""

from __future__ import annotations

import json

from tools.audit.semantic_drift_gate import (
    ClaimObject,
    build_claim_object,
    classify_event,
    compute_severity,
    run_semantic_drift_gate,
)

BASE_CONFIG = {
    "protected_files": ["README.md", "docs/SYSTEM_PROTOCOL.md"],
    "excluded_prefixes": ["archive/", "archived/"],
}


def evidence(status: str = "measured", **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "status": status,
        "substrate": "hrv",
        "signal": "gamma",
        "method": "core.gamma.estimate",
        "window": "subject",
        "controls": ["baseline"],
        "fake_alternative": "shuffle",
        "falsifier": "null-failure",
        "interpretation_boundary": "bounded",
        "replication": False,
        "external_replication": False,
        "gate_closed": False,
        "null_separation": False,
        "intervention": False,
        "generalization_authorized": False,
        "multi_substrate": False,
        "calibration_touched_external_set": False,
    }
    base.update(overrides)
    return base


def registries(
    evidence_registry: dict[str, dict[str, object]] | None = None,
    *,
    status_by_file: dict[str, str] | None = None,
    evidence_by_file: dict[str, tuple[str, ...] | list[str]] | None = None,
) -> dict[str, object]:
    return {
        "evidence": evidence_registry or {},
        "status_by_file": status_by_file or {},
        "evidence_by_file": evidence_by_file or {},
    }


def run_single(
    before: str,
    after: str,
    *,
    file_path: str = "README.md",
    evidence_registry: dict[str, dict[str, object]] | None = None,
    status: str = "measured",
    evidence_ids: tuple[str, ...] = ("ev1",),
):
    reg = registries(
        evidence_registry or {"ev1": evidence(status="measured")},
        status_by_file={file_path: status},
        evidence_by_file={file_path: evidence_ids},
    )
    report = run_semantic_drift_gate(
        diff={file_path: (before, after)},
        registries=reg,
        config=BASE_CONFIG,
    )
    event = report["events"][0] if report["events"] else None
    return report, event


def claim(
    text: str,
    *,
    file_path: str = "README.md",
    status: str = "measured",
    evidence_ids: tuple[str, ...] = ("ev1",),
    evidence_registry: dict[str, dict[str, object]] | None = None,
) -> ClaimObject:
    reg = registries(
        evidence_registry or {"ev1": evidence(status="measured")},
        status_by_file={file_path: status},
        evidence_by_file={file_path: evidence_ids},
    )
    return build_claim_object(text, file_path, reg)


# ---------------------------------------------------------------------------
# Positive pass cases
# ---------------------------------------------------------------------------


def test_lexical_rewrite_without_stronger_tier_passes():
    report, event = run_single(
        "This result is measured in this substrate.",
        "This result is measured in this dataset.",
    )
    assert report["verdict"] == "pass"
    assert event is not None
    assert event["severity"] == 0
    assert event["old_tier"] == 4
    assert event["new_tier"] == 4


def test_stronger_text_with_new_evidence_and_status_promotion_warns_per_formula():
    evidence_registry = {
        "ev_measured": evidence(status="measured"),
        "ev_validated": evidence(status="validated", replication=True, gate_closed=True),
    }
    old_claim = claim(
        "This substrate-specific result is measured.",
        status="measured",
        evidence_ids=("ev_measured",),
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This substrate-specific result is validated and replicated. evidence: ev_validated",
        status="validated",
        evidence_ids=("ev_validated",),
        evidence_registry=evidence_registry,
    )
    verdict, severity, evidence_ceiling, status_ceiling, reasons = classify_event(
        old_claim,
        new_claim,
        evidence_registry,
    )
    assert verdict == "warn"
    assert severity == 2
    assert evidence_ceiling == 6
    assert status_ceiling == 6
    assert reasons == ["lexical strengthening within authorized ceiling"]


def test_added_uncertainty_language_lowers_tier_and_passes():
    report, event = run_single(
        "This result suggests a marker.",
        "This result may indicate a marker.",
    )
    assert report["verdict"] == "pass"
    assert event is not None
    assert event["new_tier"] < event["old_tier"]


def test_status_downgrade_with_softer_wording_passes():
    evidence_registry = {"ev1": evidence(status="validated", replication=True, gate_closed=True)}
    old_claim = claim(
        "This result is validated and replicated.",
        status="validated",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result is measured.",
        status="measured",
        evidence_registry=evidence_registry,
    )
    verdict, severity, _, _, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert verdict == "pass"
    assert severity == 0
    assert reasons == []


def test_added_boundary_phrase_without_evidence_change_passes():
    report, event = run_single(
        "This result is measured.",
        "This bounded result is measured.",
    )
    assert report["verdict"] == "pass"
    assert event is not None
    assert event["boundary_removed"] is False


# ---------------------------------------------------------------------------
# Warning cases
# ---------------------------------------------------------------------------


def test_stronger_wording_within_authorized_tier_warns():
    report, event = run_single(
        "This result is consistent with the marker.",
        "This result suggests the marker.",
    )
    assert report["verdict"] == "warn"
    assert event is not None
    assert event["severity"] == 2
    assert "lexical" in event["reasons"][0]


def test_boundary_phrase_removal_but_equivalent_boundary_preserved_warns():
    report, event = run_single(
        "This is a bounded substrate-specific measured result.",
        "This is a substrate-specific measured result.",
    )
    assert report["verdict"] == "warn"
    assert event is not None
    assert event["boundary_delta"] == 1


def test_ambiguous_manuscript_style_strengthening_warns():
    report, event = run_single(
        "This result may indicate a marker.",
        "This result is consistent with the marker.",
    )
    assert report["verdict"] == "warn"
    assert event is not None
    assert event["severity"] == 2


# ---------------------------------------------------------------------------
# Hard fail rules from protocol §14
# ---------------------------------------------------------------------------


def test_hard_fail_consistent_with_to_demonstrates_without_new_evidence():
    report, event = run_single(
        "This result is consistent with the marker.",
        "This result demonstrates the marker.",
    )
    assert report["verdict"] == "fail"
    assert "consistent with -> demonstrates without new evidence object" in event["reasons"]


def test_hard_fail_candidate_to_validated_without_replication():
    report, event = run_single(
        "This candidate marker remains exploratory.",
        "This validated marker now holds.",
    )
    assert report["verdict"] == "fail"
    assert "candidate marker -> validated without replication" in event["reasons"]


def test_hard_fail_boundary_removed_while_certainty_increases():
    report, event = run_single(
        "This bounded substrate-specific result is consistent with the marker.",
        "This result demonstrates the marker.",
    )
    assert report["verdict"] == "fail"
    assert "substrate-specific or bounded removed while certainty increases" in event["reasons"]


def test_hard_fail_associated_with_to_causes_without_intervention():
    report, event = run_single(
        "This marker is associated with the outcome.",
        "This marker causes the outcome.",
    )
    assert report["verdict"] == "fail"
    assert "associated with -> causes without intervention evidence" in event["reasons"]


def test_hard_fail_measured_but_bounded_rewritten_as_proof():
    evidence_registry = {"ev1": evidence(status="measured_but_bounded", null_separation=True)}
    old_claim = claim(
        "This is a bounded positive result.",
        status="measured_but_bounded",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This is proof of the theory.",
        status="measured_but_bounded",
        evidence_registry=evidence_registry,
    )
    verdict, _, _, _, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert verdict == "fail"
    assert "measured_but_bounded claim rewritten as proof" in reasons


def test_hard_fail_honest_null_rewritten_positive():
    evidence_registry = {"ev1": evidence(status="measured")}
    old_claim = claim(
        "This result is consistent with a null outcome.",
        status="honest_null",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result suggests the theory is correct.",
        status="honest_null",
        evidence_registry=evidence_registry,
    )
    verdict, _, _, _, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert verdict == "fail"
    assert "honest_null result rewritten as support for positive theory" in reasons


def test_hard_fail_external_validation_after_touching_external_set():
    evidence_registry = {
        "ev1": evidence(
            status="validated",
            replication=True,
            gate_closed=True,
            calibration_touched_external_set=True,
        )
    }
    report, event = run_single(
        "This measured result is bounded.",
        "This external validation is validated.",
        evidence_registry=evidence_registry,
        status="validated",
    )
    assert report["verdict"] == "fail"
    assert (
        "external validation appears when calibration touched the external set" in event["reasons"]
    )


def test_hard_fail_universal_law_from_local_evidence():
    report, event = run_single(
        "This measured substrate-specific result is bounded.",
        "This universal law holds across systems.",
    )
    assert report["verdict"] == "fail"
    assert "universal or law language from local or exploratory evidence" in event["reasons"]


def test_hard_fail_readme_boundary_stripped_with_unchanged_status():
    report, event = run_single(
        "This bounded substrate-specific result is measured.",
        "This result is measured.",
        file_path="README.md",
    )
    assert report["verdict"] == "fail"
    assert "README boundary language stripped while claim status is unchanged" in event["reasons"]


def test_hard_fail_pr_title_stronger_than_evidence_allows():
    reg = registries(
        evidence_registry={"ev1": evidence(status="measured")},
        status_by_file={"PR_TITLE": "measured"},
        evidence_by_file={"PR_TITLE": ("ev1",)},
    )
    report = run_semantic_drift_gate(
        diff={"PR_TITLE": ("", "Universal law demonstrated across systems.")},
        registries=reg,
        config=BASE_CONFIG,
    )
    event = report["events"][0]
    assert report["verdict"] == "fail"
    assert "PR title stronger than changed evidence allows" in event["reasons"]


# ---------------------------------------------------------------------------
# Adversarial and resilience cases
# ---------------------------------------------------------------------------


def test_synonym_based_inflation_without_canonical_keywords_fails():
    report, event = run_single(
        "This result is consistent with the marker.",
        "This result conclusively establishes the marker.",
    )
    assert report["verdict"] == "fail"
    assert event["new_tier"] == 6


def test_evidence_id_swapped_to_weaker_evidence_fails():
    evidence_registry = {
        "ev_strong": evidence(status="validated", replication=True, gate_closed=True),
        "ev_weak": evidence(status="draft"),
    }
    old_claim = claim(
        "This result is validated.",
        status="validated",
        evidence_ids=("ev_strong",),
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result is validated. evidence: ev_weak",
        status="validated",
        evidence_ids=("ev_weak",),
        evidence_registry=evidence_registry,
    )
    verdict, _, _, _, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert verdict == "fail"
    assert "claim tier exceeds authorized ceiling" in reasons


def test_status_upgraded_in_prose_only_without_registry_auth_fails():
    report, event = run_single(
        "This result is measured.",
        "This result is validated.",
        status="measured",
    )
    assert report["verdict"] == "fail"
    assert "claim tier exceeds authorized ceiling" in event["reasons"]


def test_quoted_text_does_not_trigger_self_promotion():
    reg = registries()
    report = run_semantic_drift_gate(
        diff={"README.md": ("", "> this universal law demonstrates everything.")},
        registries=reg,
        config=BASE_CONFIG,
    )
    assert report["verdict"] == "pass"
    assert report["events"] == []


def test_archived_file_is_excluded():
    reg = registries()
    report = run_semantic_drift_gate(
        diff={"archived/README.md": ("", "This universal law demonstrates everything.")},
        registries=reg,
        config=BASE_CONFIG,
    )
    assert report["verdict"] == "pass"
    assert report["files_scanned"] == []


def test_output_json_schema_and_written_report_match_protocol(tmp_path):
    reg = registries(
        evidence_registry={"ev1": evidence(status="measured")},
        status_by_file={"README.md": "measured"},
        evidence_by_file={"README.md": ("ev1",)},
    )
    output_dir = tmp_path / "reports"
    report = run_semantic_drift_gate(
        diff={"README.md": ("This result is measured.", "This result suggests the marker.")},
        registries=reg,
        config=BASE_CONFIG,
        output_dir=output_dir,
    )
    written = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert report == written
    assert set(written) == {"protocol_version", "verdict", "files_scanned", "events", "summary"}
    assert set(written["events"][0]) == {
        "event_id",
        "file_path",
        "span_before",
        "span_after",
        "old_tier",
        "new_tier",
        "certainty_delta",
        "causality_delta",
        "scope_delta",
        "boundary_delta",
        "severity",
        "claim_status_before",
        "claim_status_after",
        "linked_evidence_ids_before",
        "linked_evidence_ids_after",
        "evidence_strength_before",
        "evidence_strength_after",
        "authorized",
        "boundary_removed",
        "reasons",
    }


# ---------------------------------------------------------------------------
# Integration with the repo's canonical 5-label claim-status taxonomy
# ---------------------------------------------------------------------------


def test_canonical_five_labels_all_have_ceilings():
    """The drift gate must recognise every label from the repo-wide taxonomy.

    ``tools.audit.claim_status_applied.CANONICAL_LABELS`` is the single
    source of truth for what ``claim_status:`` may name. If the gate's
    ``STATUS_CEILINGS`` map drifts from that list, PRs with valid
    canonical labels will be silently mis-classified.
    """

    from contracts.claim_strength import STATUS_CEILINGS
    from tools.audit.claim_status_applied import CANONICAL_LABELS

    missing = [label for label in CANONICAL_LABELS if label.lower() not in STATUS_CEILINGS]
    assert not missing, f"canonical labels missing from STATUS_CEILINGS: {missing}"


def test_unverified_analogy_ceiling_is_low_and_cannot_license_validated_prose():
    """``unverified analogy`` is the weakest canonical label; prose
    claiming ``validated`` against it must fail the ceiling check."""

    evidence_registry = {"ev1": evidence(status="measured")}
    old_claim = claim(
        "This candidate marker is consistent with the theory.",
        status="unverified analogy",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result is validated.",
        status="unverified analogy",
        evidence_registry=evidence_registry,
    )
    verdict, _, _, status_ceiling, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert status_ceiling == 1
    assert verdict == "fail"
    assert "claim tier exceeds authorized ceiling" in reasons


def test_falsified_status_cannot_license_positive_prose():
    """``falsified`` has ceiling 0 — any positive-tier prose fails."""

    evidence_registry = {"ev1": evidence(status="measured")}
    old_claim = claim(
        "This result is measured.",
        status="falsified",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result suggests the marker works.",
        status="falsified",
        evidence_registry=evidence_registry,
    )
    verdict, _, _, status_ceiling, reasons = classify_event(old_claim, new_claim, evidence_registry)
    assert status_ceiling == 0
    assert verdict == "fail"
    assert "claim tier exceeds authorized ceiling" in reasons


# ---------------------------------------------------------------------------
# Robustness: config loader
# ---------------------------------------------------------------------------


def test_load_config_accepts_real_yaml_file(tmp_path):
    """PyYAML-based loader accepts the canonical config layout."""

    import pathlib

    from tools.audit.semantic_drift_gate import load_config

    config_text = (
        "protected_files:\n"
        "  - README.md\n"
        "  - docs/X.md\n"
        "excluded_prefixes:\n"
        "  - archive/\n"
        "status_ceilings:\n"
        "  measured: 4\n"
        "  falsified: 0\n"
    )
    path = tmp_path / "conf.yaml"
    path.write_text(config_text, encoding="utf-8")
    config = load_config(pathlib.Path(path))
    assert config["protected_files"] == ["README.md", "docs/X.md"]
    assert config["excluded_prefixes"] == ["archive/"]
    assert config["status_ceilings"] == {"measured": 4, "falsified": 0}


def test_load_config_falls_back_to_canonical_defaults_when_absent(tmp_path):
    import pathlib

    from contracts.claim_strength import (
        DEFAULT_EXCLUDED_PREFIXES,
        DEFAULT_PROTECTED_FILES,
    )
    from tools.audit.semantic_drift_gate import load_config

    config = load_config(pathlib.Path(tmp_path / "does_not_exist.yaml"))
    assert config["protected_files"] == list(DEFAULT_PROTECTED_FILES)
    assert config["excluded_prefixes"] == list(DEFAULT_EXCLUDED_PREFIXES)


def test_build_diff_excludes_pr_surfaces_when_enforce_flag_off(tmp_path, monkeypatch):
    """``enforce_pr_surfaces: false`` → PR_TITLE / PR_BODY not in the diff."""

    from tools.audit import semantic_drift_gate as mod

    monkeypatch.setattr(mod, "_git_changed_files", lambda *_a, **_k: [])
    monkeypatch.setattr(mod, "_git_show", lambda *_a, **_k: "")
    monkeypatch.setattr(mod, "_working_tree_text", lambda *_a, **_k: "")

    diff = mod._build_diff_from_git(
        tmp_path,
        "base",
        "head",
        "Universal law demonstrated",
        "claim_status: validated",
        enforce_pr_surfaces=False,
    )
    assert "PR_TITLE" not in diff
    assert "PR_BODY" not in diff


def test_build_diff_includes_pr_surfaces_when_enforce_flag_on(tmp_path, monkeypatch):
    from tools.audit import semantic_drift_gate as mod

    monkeypatch.setattr(mod, "_git_changed_files", lambda *_a, **_k: [])
    monkeypatch.setattr(mod, "_git_show", lambda *_a, **_k: "")
    monkeypatch.setattr(mod, "_working_tree_text", lambda *_a, **_k: "")

    diff = mod._build_diff_from_git(
        tmp_path,
        "base",
        "head",
        "title",
        "body",
        enforce_pr_surfaces=True,
    )
    assert diff["PR_TITLE"] == ("", "title")
    assert diff["PR_BODY"] == ("", "body")


def test_severity_function_matches_protocol_exactly():
    evidence_registry = {"ev1": evidence(status="measured")}
    old_claim = claim(
        "This bounded substrate-specific result is consistent with the marker.",
        status="measured",
        evidence_registry=evidence_registry,
    )
    new_claim = claim(
        "This result demonstrates the marker.",
        status="measured",
        evidence_registry=evidence_registry,
    )
    severity = compute_severity(old_claim, new_claim, evidence_registry)
    assert severity == 12.0
