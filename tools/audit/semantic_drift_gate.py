"""Semantic drift enforcement gate.

Deterministic audit that blocks prose from outrunning evidence and
authorized claim status.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import pathlib
import subprocess
from collections.abc import Iterable, Mapping

import yaml

from contracts.claim_strength import (
    DEFAULT_EXCLUDED_PREFIXES,
    DEFAULT_PROTECTED_FILES,
    POSITIVE_CLAIM_MIN_TIER,
    PROOF_OR_VALIDATION_MARKERS,
    PROTOCOL_VERSION,
    SPECIAL_SURFACES,
)
from tools.audit.claim_span_extractor import (
    align_claim_spans,
    assign_tier,
    classify_causality,
    classify_scope,
    contains_phrase,
    extract_boundary_markers,
    extract_inline_claim_status,
    extract_linked_evidence_ids,
)
from tools.audit.evidence_ceiling import (
    ceiling_from_evidence_object,
    resolve_evidence_ceiling,
    resolve_status_ceiling,
)

__all__ = [
    "ClaimObject",
    "classify_event",
    "compute_severity",
    "load_config",
    "main",
    "run_semantic_drift_gate",
    "write_markdown_report",
    "write_json_report",
]


@dataclasses.dataclass(frozen=True)
class ClaimObject:
    claim_id: str
    text_span: str
    file_path: str
    tier: int
    scope: int
    causality_level: int
    certainty_level: int
    boundary_markers: tuple[str, ...]
    linked_evidence_ids: tuple[str, ...]
    linked_claim_status: str


def load_config(path: pathlib.Path) -> dict[str, object]:
    """Load the drift-gate YAML config; fall back to canonical defaults."""

    if not path.exists():
        return {
            "protected_files": list(DEFAULT_PROTECTED_FILES),
            "excluded_prefixes": list(DEFAULT_EXCLUDED_PREFIXES),
        }
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"expected mapping at top level of {path}; got {type(parsed).__name__}")
    parsed.setdefault("protected_files", list(DEFAULT_PROTECTED_FILES))
    parsed.setdefault("excluded_prefixes", list(DEFAULT_EXCLUDED_PREFIXES))
    return parsed


def _default_registries() -> dict[str, dict[str, object]]:
    return {
        "evidence": {},
        "status_by_file": {},
        "evidence_by_file": {},
    }


def _load_json(path: pathlib.Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_registries(repo_root: pathlib.Path) -> dict[str, dict[str, object]]:
    registries = _default_registries()
    evidence_candidates = (
        repo_root / "evidence" / "semantic_drift_registry.json",
        repo_root / "evidence" / "evidence_registry.json",
    )
    status_candidates = (
        repo_root / "contracts" / "claim_status_registry.json",
        repo_root / "contracts" / "status_registry.json",
    )
    for candidate in evidence_candidates:
        if candidate.exists():
            registries["evidence"] = _load_json(candidate)
            break
    for candidate in status_candidates:
        if candidate.exists():
            registries["status_by_file"] = _load_json(candidate)
            break
    return registries


def _protected(path: str, config: Mapping[str, object]) -> bool:
    if path in SPECIAL_SURFACES:
        return True
    excluded_prefixes = tuple(
        str(item) for item in config.get("excluded_prefixes", DEFAULT_EXCLUDED_PREFIXES)
    )
    if any(path.startswith(prefix) for prefix in excluded_prefixes):
        return False
    protected = {str(item) for item in config.get("protected_files", DEFAULT_PROTECTED_FILES)}
    if path in protected:
        return True
    return path.startswith("manuscript/")


def _claim_id(file_path: str, text_span: str) -> str:
    payload = f"{file_path}\n{text_span}".encode()
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()[:12]


def _resolve_status(span: str, file_path: str, status_registry: Mapping[str, object]) -> str:
    inline = extract_inline_claim_status(span)
    if inline:
        return inline
    raw = status_registry.get(file_path, "")
    if isinstance(raw, str):
        return raw.strip().lower()
    return ""


def build_claim_object(
    span: str,
    file_path: str,
    registries: Mapping[str, Mapping[str, object]],
) -> ClaimObject:
    evidence_ids = extract_linked_evidence_ids(span)
    if not evidence_ids:
        fallback = registries.get("evidence_by_file", {}).get(file_path, ())
        evidence_ids = tuple(str(item) for item in fallback)
    status = _resolve_status(span, file_path, registries.get("status_by_file", {}))
    tier = assign_tier(span)
    scope = classify_scope(span)
    causality = classify_causality(span)
    boundaries = extract_boundary_markers(span)
    return ClaimObject(
        claim_id=_claim_id(file_path, span),
        text_span=span,
        file_path=file_path,
        tier=tier,
        scope=scope,
        causality_level=causality,
        certainty_level=tier,
        boundary_markers=boundaries,
        linked_evidence_ids=evidence_ids,
        linked_claim_status=status,
    )


def _new_qualifying_evidence_added(
    before_ids: tuple[str, ...],
    after_ids: tuple[str, ...],
    evidence_registry: Mapping[str, Mapping[str, object]],
) -> bool:
    before = set(before_ids)
    new_ids = [evidence_id for evidence_id in after_ids if evidence_id not in before]
    return any(
        ceiling_from_evidence_object(evidence_registry.get(evidence_id, {})) > 0
        for evidence_id in new_ids
    )


def _status_legally_upgraded(before_status: str, after_status: str) -> bool:
    return resolve_status_ceiling(after_status) > resolve_status_ceiling(before_status)


def compute_severity(
    old_claim: ClaimObject,
    new_claim: ClaimObject,
    evidence_registry: Mapping[str, Mapping[str, object]],
) -> float:
    delta_tier = max(0, new_claim.tier - old_claim.tier)
    delta_causality = max(0, new_claim.causality_level - old_claim.causality_level)
    delta_scope = max(0, new_claim.scope - old_claim.scope)
    removed_boundaries = set(old_claim.boundary_markers) - set(new_claim.boundary_markers)
    delta_boundary = float(len(removed_boundaries))
    proof_bonus = (
        2
        if any(
            contains_phrase(new_claim.text_span.lower(), marker)
            for marker in PROOF_OR_VALIDATION_MARKERS
        )
        else 0
    )
    evidence_bonus = (
        2
        if _new_qualifying_evidence_added(
            old_claim.linked_evidence_ids,
            new_claim.linked_evidence_ids,
            evidence_registry,
        )
        else 0
    )
    status_bonus = (
        2
        if _status_legally_upgraded(
            old_claim.linked_claim_status,
            new_claim.linked_claim_status,
        )
        else 0
    )

    severity = (
        2 * delta_tier
        + 2 * delta_causality
        + 2 * delta_scope
        + 1.5 * delta_boundary
        + proof_bonus
        - evidence_bonus
        - status_bonus
    )

    after_evidence = [
        evidence_registry.get(evidence_id, {}) for evidence_id in new_claim.linked_evidence_ids
    ]

    if contains_phrase(new_claim.text_span.lower(), "validated") and not any(
        bool(evidence.get("replication")) or bool(evidence.get("external_replication"))
        for evidence in after_evidence
    ):
        severity += 4
    if new_claim.causality_level >= 4 and not any(
        bool(evidence.get("intervention")) for evidence in after_evidence
    ):
        severity += 4
    if any(
        contains_phrase(new_claim.text_span.lower(), marker) for marker in ("universal", "law")
    ) and not any(
        bool(evidence.get("generalization_authorized")) and bool(evidence.get("multi_substrate"))
        for evidence in after_evidence
    ):
        severity += 4
    if old_claim.boundary_markers and not new_claim.boundary_markers:
        severity += 3
    if new_claim.tier >= POSITIVE_CLAIM_MIN_TIER and new_claim.linked_claim_status in {
        "honest_null",
        "honest_negative",
        "falsified",
    }:
        severity += 3
    return severity


def _file_surface_kind(file_path: str) -> str:
    if file_path == "PR_TITLE":
        return "PR title"
    if file_path == "PR_BODY":
        return "PR body"
    return file_path


def _hard_failures(
    old_claim: ClaimObject,
    new_claim: ClaimObject,
    evidence_registry: Mapping[str, Mapping[str, object]],
    authorized_ceiling: int,
) -> list[str]:
    reasons: list[str] = []
    new_text = new_claim.text_span.lower()
    old_text = old_claim.text_span.lower()

    new_evidence_added = _new_qualifying_evidence_added(
        old_claim.linked_evidence_ids,
        new_claim.linked_evidence_ids,
        evidence_registry,
    )
    after_evidence = [
        evidence_registry.get(evidence_id, {}) for evidence_id in new_claim.linked_evidence_ids
    ]

    if (
        contains_phrase(old_text, "consistent with")
        and contains_phrase(new_text, "demonstrates")
        and not new_evidence_added
    ):
        reasons.append("consistent with -> demonstrates without new evidence object")
    if (
        contains_phrase(old_text, "candidate")
        and contains_phrase(new_text, "validated")
        and not any(
            bool(evidence.get("replication")) or bool(evidence.get("external_replication"))
            for evidence in after_evidence
        )
    ):
        reasons.append("candidate marker -> validated without replication")
    if (
        any(marker in old_claim.boundary_markers for marker in ("substrate-specific", "bounded"))
        and not any(
            marker in new_claim.boundary_markers for marker in ("substrate-specific", "bounded")
        )
        and new_claim.tier > old_claim.tier
    ):
        reasons.append("substrate-specific or bounded removed while certainty increases")
    if (
        contains_phrase(old_text, "associated with")
        and contains_phrase(new_text, "causes")
        and not any(bool(evidence.get("intervention")) for evidence in after_evidence)
    ):
        reasons.append("associated with -> causes without intervention evidence")
    if old_claim.linked_claim_status == "measured_but_bounded" and contains_phrase(
        new_text, "proof"
    ):
        reasons.append("measured_but_bounded claim rewritten as proof")
    if old_claim.linked_claim_status == "honest_null" and new_claim.tier >= POSITIVE_CLAIM_MIN_TIER:
        reasons.append("honest_null result rewritten as support for positive theory")
    if contains_phrase(new_text, "external validation") and any(
        bool(evidence.get("calibration_touched_external_set")) for evidence in after_evidence
    ):
        reasons.append("external validation appears when calibration touched the external set")
    if any(contains_phrase(new_text, marker) for marker in ("universal", "law")) and not any(
        bool(evidence.get("generalization_authorized")) and bool(evidence.get("multi_substrate"))
        for evidence in after_evidence
    ):
        reasons.append("universal or law language from local or exploratory evidence")
    if (
        new_claim.file_path == "README.md"
        and bool(old_claim.boundary_markers)
        and not bool(new_claim.boundary_markers)
        and old_claim.linked_claim_status == new_claim.linked_claim_status
    ):
        reasons.append("README boundary language stripped while claim status is unchanged")
    if new_claim.file_path in SPECIAL_SURFACES and new_claim.tier > authorized_ceiling:
        reasons.append(
            f"{_file_surface_kind(new_claim.file_path)} stronger than changed evidence allows"
        )
    return reasons


# Reason strings that elevate an event to a hard-fail regardless of
# severity. Any new hard-fail reason must be added here *and* returned
# by _hard_failures (or classify_event's ceiling check) so summary and
# aggregate stay consistent without ad-hoc string matching.
_HARD_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "consistent with -> demonstrates without new evidence object",
        "candidate marker -> validated without replication",
        "substrate-specific or bounded removed while certainty increases",
        "associated with -> causes without intervention evidence",
        "measured_but_bounded claim rewritten as proof",
        "honest_null result rewritten as support for positive theory",
        "external validation appears when calibration touched the external set",
        "universal or law language from local or exploratory evidence",
        "README boundary language stripped while claim status is unchanged",
        "PR title stronger than changed evidence allows",
        "PR body stronger than changed evidence allows",
        "claim tier exceeds authorized ceiling",
        "severity threshold exceeded",
    }
)


def _event_is_fail(severity: float, reasons: Iterable[str]) -> bool:
    if float(severity) >= 4:
        return True
    return any(reason in _HARD_FAIL_REASONS for reason in reasons)


def classify_event(
    old_claim: ClaimObject,
    new_claim: ClaimObject,
    evidence_registry: Mapping[str, Mapping[str, object]],
) -> tuple[str, float, int, int, list[str]]:
    evidence_ceiling = resolve_evidence_ceiling(new_claim.linked_evidence_ids, evidence_registry)
    status_ceiling = resolve_status_ceiling(new_claim.linked_claim_status)
    authorized_ceiling = min(evidence_ceiling, status_ceiling)
    severity = compute_severity(old_claim, new_claim, evidence_registry)
    reasons = _hard_failures(old_claim, new_claim, evidence_registry, authorized_ceiling)

    if new_claim.tier > authorized_ceiling:
        reasons.append("claim tier exceeds authorized ceiling")

    if _event_is_fail(severity, reasons):
        if not reasons:
            reasons = ["severity threshold exceeded"]
        return "fail", severity, evidence_ceiling, status_ceiling, reasons
    if severity > 0 or reasons:
        return (
            "warn",
            severity,
            evidence_ceiling,
            status_ceiling,
            reasons or ["lexical strengthening within authorized ceiling"],
        )
    return "pass", severity, evidence_ceiling, status_ceiling, []


def _event_record(
    event_id: str,
    file_path: str,
    old_claim: ClaimObject,
    new_claim: ClaimObject,
    severity: float,
    verdict: str,
    evidence_ceiling_before: int,
    evidence_ceiling_after: int,
    status_ceiling_after: int,
    reasons: list[str],
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "file_path": file_path,
        "span_before": old_claim.text_span,
        "span_after": new_claim.text_span,
        "old_tier": old_claim.tier,
        "new_tier": new_claim.tier,
        "certainty_delta": max(0, new_claim.certainty_level - old_claim.certainty_level),
        "causality_delta": max(0, new_claim.causality_level - old_claim.causality_level),
        "scope_delta": max(0, new_claim.scope - old_claim.scope),
        "boundary_delta": len(set(old_claim.boundary_markers) - set(new_claim.boundary_markers)),
        "severity": severity,
        "claim_status_before": old_claim.linked_claim_status,
        "claim_status_after": new_claim.linked_claim_status,
        "linked_evidence_ids_before": list(old_claim.linked_evidence_ids),
        "linked_evidence_ids_after": list(new_claim.linked_evidence_ids),
        "evidence_strength_before": evidence_ceiling_before,
        "evidence_strength_after": evidence_ceiling_after,
        "authorized": verdict == "pass",
        "boundary_removed": bool(set(old_claim.boundary_markers) - set(new_claim.boundary_markers)),
        "reasons": reasons,
    }


def _aggregate_verdict(events: Iterable[dict[str, object]]) -> str:
    event_list = list(events)
    if any(_event_is_fail(event["severity"], event.get("reasons") or []) for event in event_list):
        return "fail"
    if any(float(event["severity"]) > 0 or event.get("reasons") for event in event_list):
        return "warn"
    return "pass"


def write_json_report(report: Mapping[str, object], output_path: pathlib.Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")


def write_markdown_report(report: Mapping[str, object], output_path: pathlib.Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Semantic Drift Report",
        "",
        f"- protocol_version: {report['protocol_version']}",
        f"- verdict: {report['verdict']}",
        f"- files_scanned: {len(report['files_scanned'])}",
        f"- total_events: {report['summary']['total_events']}",
        f"- warn_events: {report['summary']['warn_events']}",
        f"- fail_events: {report['summary']['fail_events']}",
        "",
    ]
    for event in report["events"]:
        lines.extend(
            [
                f"## {event['event_id']} — {event['file_path']}",
                "",
                f"- severity: {event['severity']}",
                f"- old_tier: {event['old_tier']}",
                f"- new_tier: {event['new_tier']}",
                f"- reasons: {', '.join(event['reasons']) or 'none'}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_semantic_drift_gate(
    diff: Mapping[str, tuple[str, str]],
    registries: Mapping[str, Mapping[str, object]] | None = None,
    config: Mapping[str, object] | None = None,
    output_dir: pathlib.Path | None = None,
) -> dict[str, object]:
    active_registries = _default_registries()
    if registries:
        for key, value in registries.items():
            active_registries[key] = dict(value)

    active_config: dict[str, object] = {
        "protected_files": list(DEFAULT_PROTECTED_FILES),
        "excluded_prefixes": list(DEFAULT_EXCLUDED_PREFIXES),
    }
    if config:
        active_config.update(dict(config))

    events: list[dict[str, object]] = []
    files_scanned: list[str] = []
    event_counter = 0

    for file_path, (before_text, after_text) in diff.items():
        if not _protected(file_path, active_config):
            continue
        files_scanned.append(file_path)
        for old_span, new_span in align_claim_spans(before_text, after_text):
            old_claim = (
                build_claim_object(old_span, file_path, active_registries)
                if old_span
                else ClaimObject(
                    claim_id=_claim_id(file_path, ""),
                    text_span="",
                    file_path=file_path,
                    tier=0,
                    scope=0,
                    causality_level=0,
                    certainty_level=0,
                    boundary_markers=(),
                    linked_evidence_ids=tuple(
                        str(item)
                        for item in active_registries.get("evidence_by_file", {}).get(file_path, ())
                    ),
                    linked_claim_status=str(
                        active_registries.get("status_by_file", {}).get(file_path, "")
                    ).lower(),
                )
            )
            new_claim = (
                build_claim_object(new_span, file_path, active_registries)
                if new_span
                else ClaimObject(
                    claim_id=_claim_id(file_path, ""),
                    text_span="",
                    file_path=file_path,
                    tier=0,
                    scope=0,
                    causality_level=0,
                    certainty_level=0,
                    boundary_markers=(),
                    linked_evidence_ids=tuple(
                        str(item)
                        for item in active_registries.get("evidence_by_file", {}).get(file_path, ())
                    ),
                    linked_claim_status=str(
                        active_registries.get("status_by_file", {}).get(file_path, "")
                    ).lower(),
                )
            )
            verdict, severity, evidence_after, status_after, reasons = classify_event(
                old_claim,
                new_claim,
                active_registries.get("evidence", {}),
            )
            evidence_before = resolve_evidence_ceiling(
                old_claim.linked_evidence_ids,
                active_registries.get("evidence", {}),
            )
            event_counter += 1
            events.append(
                _event_record(
                    event_id=f"drift-{event_counter:04d}",
                    file_path=file_path,
                    old_claim=old_claim,
                    new_claim=new_claim,
                    severity=severity,
                    verdict=verdict,
                    evidence_ceiling_before=evidence_before,
                    evidence_ceiling_after=evidence_after,
                    status_ceiling_after=status_after,
                    reasons=reasons,
                )
            )

    verdict = _aggregate_verdict(events)
    fail_events = sum(
        1 for event in events if _event_is_fail(event["severity"], event.get("reasons") or [])
    )
    warn_events = sum(
        1
        for event in events
        if not _event_is_fail(event["severity"], event.get("reasons") or [])
        and (float(event["severity"]) > 0 or event.get("reasons"))
    )
    report = {
        "protocol_version": PROTOCOL_VERSION,
        "verdict": verdict,
        "files_scanned": files_scanned,
        "events": events,
        "summary": {
            "total_events": len(events),
            "warn_events": warn_events,
            "fail_events": fail_events,
        },
    }

    if output_dir is not None:
        json_path = output_dir / "latest.json"
        markdown_path = output_dir / "latest.md"
        write_json_report(report, json_path)
        write_markdown_report(report, markdown_path)
    return report


def _git_changed_files(repo_root: pathlib.Path, base_ref: str, head_ref: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", "--name-only", base_ref, head_ref],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _git_show(repo_root: pathlib.Path, ref: str, path: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "show", f"{ref}:{path}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return ""


def _working_tree_text(repo_root: pathlib.Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8")


def _build_diff_from_git(
    repo_root: pathlib.Path,
    base_ref: str,
    head_ref: str,
    pr_title: str,
    pr_body: str,
    *,
    enforce_pr_surfaces: bool = True,
) -> dict[str, tuple[str, str]]:
    diff: dict[str, tuple[str, str]] = {}
    for path in _git_changed_files(repo_root, base_ref, head_ref):
        diff[path] = (_git_show(repo_root, base_ref, path), _working_tree_text(repo_root, path))
    if enforce_pr_surfaces:
        if pr_title:
            diff["PR_TITLE"] = ("", pr_title)
        if pr_body:
            diff["PR_BODY"] = ("", pr_body)
    return diff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the semantic drift enforcement gate.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--base-ref", default="HEAD~1", help="Base git ref.")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref.")
    parser.add_argument(
        "--config",
        default="contracts/semantic_drift_config.yaml",
        help="Path to semantic drift config, relative to repo root unless absolute.",
    )
    parser.add_argument("--pr-title", default=os.environ.get("GH_PR_TITLE", ""))
    parser.add_argument("--pr-body", default=os.environ.get("GH_PR_BODY", ""))
    args = parser.parse_args(argv)

    repo_root = pathlib.Path(args.repo_root).resolve()
    config_path = pathlib.Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    config = load_config(config_path)
    registries = load_registries(repo_root)
    enforce_pr_surfaces = bool(config.get("enforce_pr_surfaces", True))
    diff = _build_diff_from_git(
        repo_root,
        args.base_ref,
        args.head_ref,
        args.pr_title,
        args.pr_body,
        enforce_pr_surfaces=enforce_pr_surfaces,
    )
    output_dir = repo_root / "reports" / "semantic_drift"
    report = run_semantic_drift_gate(
        diff=diff, registries=registries, config=config, output_dir=output_dir
    )
    return 2 if report["verdict"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
