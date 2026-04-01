#!/usr/bin/env python3
"""Deterministic reference runner for demo bundles.

This runner validates canonical artifacts, computes scores/gates/classification,
and emits an EvaluationResult with deterministic execution-state chain claims.
"""

import argparse
import hashlib
import json
import re
import subprocess
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import jsonschema
from jsonschema import RefResolver

warnings.filterwarnings("ignore", category=DeprecationWarning)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

PHASES = [
    "artifact_validation",
    "admissibility_derivation",
    "task_scoring",
    "domain_scoring",
    "gate_evaluation",
    "classification",
    "finalization",
]
CHAIN_FORMAT_VERSION = "execution_chain.v1"
CHAIN_STEP_HASH_DOMAIN = "kriterion.execution_chain.step"
CHAIN_GENESIS_DOMAIN = "kriterion.execution_chain.genesis"

CRITICAL_GIT_PATHS = ["tools", "schemas", "execution", "governance", ".github/workflows"]


def canonical_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_obj(data: Any) -> Any:
    return json.loads(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_step_hash(*, chain_format_version: str, phase_id: str, phase_input_digest: str, previous_step_hash: str, contract_version: str) -> str:
    step_input = {
        "chain_format_version": chain_format_version,
        "phase_id": phase_id,
        "phase_input_digest": phase_input_digest,
        "previous_step_hash": previous_step_hash,
        "contract_version": contract_version,
    }
    payload = {"domain": CHAIN_STEP_HASH_DOMAIN, "step_hash_input": step_input}
    return sha256_hex(canonical_bytes(payload))


def build_genesis_hash(bundle: Dict[str, Any], chain_format_version: str) -> tuple[str, str]:
    bundle_hash = sha256_hex(canonical_bytes(canonical_obj(bundle)))
    genesis_payload = {
        "domain": CHAIN_GENESIS_DOMAIN,
        "bundle_hash": bundle_hash,
        "chain_format_version": chain_format_version,
    }
    return bundle_hash, sha256_hex(canonical_bytes(genesis_payload))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance: Any, schema_name: str) -> Tuple[bool, str]:
    schema = load_json(SCHEMAS / schema_name)
    store = {}
    for path in SCHEMAS.glob("*.json"):
        s = load_json(path)
        store[path.name] = s
        if "$id" in s:
            store[s["$id"]] = s
    resolver = RefResolver(base_uri=SCHEMAS.as_uri() + "/", referrer=schema, store=store)
    try:
        jsonschema.validate(instance=instance, schema=schema, resolver=resolver)
        return True, "VALID"
    except jsonschema.ValidationError as exc:
        return False, exc.validator or "INVALID_SCHEMA"


def assert_git_authoritative(*, allow_non_authoritative_git: bool) -> None:
    if allow_non_authoritative_git:
        return

    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise SystemExit("GIT_AUTHORITY_INVALID: repository is not a valid git worktree")

    for cmd in (["git", "diff", "--quiet"], ["git", "diff", "--cached", "--quiet"]):
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            raise SystemExit("GIT_AUTHORITY_INVALID: tracked-file modifications detected")

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", *CRITICAL_GIT_PATHS],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        raise SystemExit("GIT_AUTHORITY_INVALID: unable to enumerate untracked files")
    if any(line.strip() for line in untracked.stdout.splitlines()):
        raise SystemExit("GIT_AUTHORITY_INVALID: untracked files in critical execution/governance paths")


INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+previous\s+instructions\b", flags=re.IGNORECASE),
    re.compile(r"\boverride\s+protocol\b", flags=re.IGNORECASE),
    re.compile(r"\bset\s+gate\s+to\s+pass\b", flags=re.IGNORECASE),
    re.compile(r"\bchange\s+scoring\s+logic\b", flags=re.IGNORECASE),
    re.compile(r"\bassistant\s+must\s+output\b", flags=re.IGNORECASE),
]


def contains_injection(value: Any) -> bool:
    if isinstance(value, str):
        compact = re.sub(r"\s+", " ", value)
        return any(pattern.search(compact) for pattern in INJECTION_PATTERNS)
    if isinstance(value, dict):
        return any(contains_injection(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_injection(v) for v in value)
    return False


def verify_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    ok, reason = validate(artifact, "canonical-artifact.schema.json")
    schema_status = "VALID" if ok else reason if reason.startswith("INVALID") else "INVALID_SCHEMA"
    integrity_status = "VALID"
    reason_codes: List[str] = []
    admissible = ok

    if ok:
        if contains_injection(artifact):
            raise SystemExit("INJECTION_DETECTED — evaluation halted (fail-closed)")
        payload_hash = sha256_hex(canonical_bytes(artifact["payload"]))
        if artifact["fingerprint"]["sha256"] != payload_hash:
            integrity_status = "INVALID_FINGERPRINT"
            reason_codes.append("INVALID_FINGERPRINT")
            admissible = False
        elif artifact["evidence_class"] == "HIGH" and not artifact["reviewer"]["reviewer_independence"]:
            integrity_status = "REVIEWER_INDEPENDENCE_MISSING"
            reason_codes.append("REVIEWER_INDEPENDENCE_MISSING")
            admissible = False

    return {
        "artifact_id": artifact.get("artifact_id", "UNKNOWN_ARTIFACT"),
        "schema_status": schema_status if schema_status in {"VALID", "INVALID_SCHEMA", "INVALID_TYPE", "INVALID_REQUIRED_FIELD", "INVALID_ENUM", "INVALID_PATTERN"} else "INVALID_SCHEMA",
        "integrity_status": integrity_status,
        "admissible": admissible,
        "reason_codes": reason_codes,
    }


def _capsule_artifact_validation(artifact_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for r in sorted(artifact_results, key=lambda x: x["artifact_id"]):
        rows.append(
            {
                "artifact_id": r["artifact_id"],
                "schema_status": r["schema_status"],
                "integrity_status": r["integrity_status"],
                "admissible": r["admissible"],
                "reason_codes": sorted(r.get("reason_codes", [])),
            }
        )
    return {"artifact_validation_results": rows}


def _capsule_admissibility(admissible_ids: set[str], id_to_artifact: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    aids = sorted(admissible_ids)
    fps = sorted(id_to_artifact[aid]["fingerprint"]["sha256"] for aid in aids)
    return {"admitted_artifact_ids": aids, "admitted_artifact_fingerprints": fps}


def _capsule_task_scoring(task_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for t in sorted(task_scores, key=lambda x: (x["domain_id"], x["task_id"])):
        rows.append(
            {
                "domain_id": t["domain_id"],
                "task_id": t["task_id"],
                "final_score": float(t["final_score"]),
                "evidence_artifact_ids": sorted(t["evidence_artifact_ids"]),
                "reason_codes": sorted(t.get("reason_codes", [])),
            }
        )
    return {"task_scores": rows}


def _capsule_domain_scoring(domain_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for d in sorted(domain_scores, key=lambda x: x["domain_id"]):
        rows.append(
            {
                "domain_id": d["domain_id"],
                "final_domain_score": float(d["final_domain_score"]),
                "domain_cap": float(d["domain_cap"]),
                "evidence_class_distribution": d["evidence_class_distribution"],
            }
        )
    return {"domain_scores": rows}


def _capsule_gate_evaluation(gate_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for g in sorted(gate_results, key=lambda x: x["gate_id"]):
        rows.append({"gate_id": g["gate_id"], "status": g["status"], "blocking": g["blocking"]})
    return {"gate_results": rows}


def _capsule_classification(final_classification: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "classification": {
            "status": final_classification["status"],
            "classification_label": final_classification["classification_label"],
            "composite_score": float(final_classification["composite_score"]),
        }
    }


def _capsule_finalization(bundle: Dict[str, Any], artifact_count: int, ts: str, evidence_trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "finalization": {
            "target_protocol_id": bundle["target_protocol_id"],
            "execution_mode": bundle["execution_mode"],
            "evaluation_timestamp": ts,
            "artifact_count": artifact_count,
            "evidence_trace_digest": sha256_hex(canonical_bytes(canonical_obj(evidence_trace))),
        }
    }


def _build_chain(*, bundle: Dict[str, Any], ts: str, protocol_version: str, artifact_results: List[Dict[str, Any]], admissible_ids: set[str], id_to_artifact: Dict[str, Dict[str, Any]], task_scores: List[Dict[str, Any]], domain_scores: List[Dict[str, Any]], gate_results: List[Dict[str, Any]], final_classification: Dict[str, Any], evidence_trace: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    g0_status = "FAIL" if any(not r["admissible"] for r in artifact_results) else "PASS"
    capsules: Dict[str, Dict[str, Any]] = {
        "artifact_validation": _capsule_artifact_validation(artifact_results),
        "admissibility_derivation": _capsule_admissibility(admissible_ids, id_to_artifact),
        "task_scoring": _capsule_task_scoring(task_scores),
        "domain_scoring": _capsule_domain_scoring(domain_scores),
        "gate_evaluation": _capsule_gate_evaluation(gate_results),
        "classification": _capsule_classification(final_classification),
        "finalization": _capsule_finalization(bundle, len(bundle["artifacts"]), ts, evidence_trace),
    }

    chain: List[Dict[str, Any]] = []
    _, previous = build_genesis_hash(bundle, CHAIN_FORMAT_VERSION)

    for idx, phase_id in enumerate(PHASES):
        gate_state: Dict[str, str] = {}
        if phase_id == "artifact_validation":
            gate_state = {"G0_INTEGRITY": g0_status}
        elif phase_id in {"gate_evaluation", "classification", "finalization"}:
            gate_state = {g["gate_id"]: g["status"] for g in sorted(gate_results, key=lambda x: x["gate_id"])}

        capsule = {
            "admitted_artifact_ids": sorted(admissible_ids),
            "admitted_artifact_fingerprints": sorted(id_to_artifact[aid]["fingerprint"]["sha256"] for aid in sorted(admissible_ids)),
            "gate_state": gate_state,
            "phase_material": capsules[phase_id],
        }
        phase_components = {"phase_id": phase_id, "replay_capsule": capsule}
        phase_input_digest = sha256_hex(canonical_bytes(canonical_obj(phase_components)))
        step_hash = build_step_hash(
            chain_format_version=CHAIN_FORMAT_VERSION,
            phase_id=phase_id,
            phase_input_digest=phase_input_digest,
            previous_step_hash=previous,
            contract_version=protocol_version,
        )
        chain.append(
            {
                "phase_index": idx,
                "phase_id": phase_id,
                "previous_step_hash": previous,
                "step_hash": step_hash,
                "contract_version": protocol_version,
                "phase_input_digest": phase_input_digest,
                "replay_capsule": capsule,
            }
        )
        previous = step_hash

    return chain, previous


def compute(bundle: Dict[str, Any]) -> Dict[str, Any]:
    artifact_results = [verify_artifact(a) for a in bundle["artifacts"]]
    admissible_ids = {r["artifact_id"] for r in artifact_results if r["admissible"]}

    seen = {}
    id_to_artifact = {a["artifact_id"]: a for a in bundle["artifacts"]}
    for a in bundle["artifacts"]:
        aid = a["artifact_id"]
        if aid not in admissible_ids:
            continue
        fp = a["fingerprint"]["sha256"]
        if fp in seen:
            for r in artifact_results:
                if r["artifact_id"] in {aid, seen[fp]}:
                    r["integrity_status"] = "DUPLICATE_EVIDENCE"
                    r["admissible"] = False
                    if "DUPLICATE_EVIDENCE" not in r["reason_codes"]:
                        r["reason_codes"].append("DUPLICATE_EVIDENCE")
            admissible_ids.discard(aid)
            admissible_ids.discard(seen[fp])
        else:
            seen[fp] = aid

    task_scores = []
    evidence_trace = []
    domains_meta = {}
    for task in bundle["tasks"]:
        domains_meta[task["domain_id"]] = (task["domain_name"], task["must_have"])
        missing_required = any(aid not in admissible_ids for aid in task["required_artifact_ids"])
        admissible_task_ids = [aid for aid in task["evidence_artifact_ids"] if aid in admissible_ids]
        penalties = list(task.get("penalties_applied", []))
        reasons = list(task.get("reason_codes", []))
        raw = float(task["raw_score"])
        cap = float(task["evidence_cap"])
        if missing_required or not admissible_task_ids:
            final = 0.0
            if missing_required:
                penalties.append("MISSING_REQUIRED_EVIDENCE")
                reasons.append("MISSING_REQUIRED_EVIDENCE")
            if not admissible_task_ids:
                penalties.append("NO_ADMISSIBLE_EVIDENCE")
                reasons.append("NO_ADMISSIBLE_EVIDENCE")
        else:
            final = min(raw, cap)
        task_scores.append(
            {
                "protocol_id": bundle["target_protocol_id"],
                "domain_id": task["domain_id"],
                "task_id": task["task_id"],
                "task_weight": task["task_weight"],
                "evidence_artifact_ids": admissible_task_ids,
                "raw_score": raw,
                "evidence_cap": cap,
                "penalties_applied": penalties,
                "final_score": final,
                "reason_codes": reasons,
            }
        )
        for aid in admissible_task_ids:
            evidence_trace.append(
                {
                    "artifact_id": aid,
                    "artifact_type": id_to_artifact[aid]["artifact_type"],
                    "domain_id": task["domain_id"],
                    "task_id": task["task_id"],
                    "task_score_contribution": final,
                    "domain_score_contribution": 0.0,
                    "evidence_class": id_to_artifact[aid]["evidence_class"],
                    "trace_status": "USED",
                }
            )

    grouped = defaultdict(list)
    for ts in task_scores:
        grouped[ts["domain_id"]].append(ts)

    domain_scores = []
    for domain_id, items in grouped.items():
        dname, must_have = domains_meta[domain_id]
        weighted = sum(item["task_weight"] * item["final_score"] for item in items) / 100.0
        dist = {"LOW": 0, "MED": 0, "HIGH": 0}
        for item in items:
            for aid in item["evidence_artifact_ids"]:
                dist[id_to_artifact[aid]["evidence_class"]] += 1
        if dist["HIGH"] > 0:
            cap = 5.0
        elif dist["MED"] > 0:
            cap = 4.0
        elif dist["LOW"] > 0:
            cap = 3.0
        else:
            cap = 0.0
        final_domain = min(weighted, cap)
        domain_scores.append(
            {
                "domain_id": domain_id,
                "domain_name": dname,
                "must_have": must_have,
                "weighted_score": weighted,
                "evidence_class_distribution": dist,
                "domain_cap": cap,
                "final_domain_score": final_domain,
            }
        )
        for row in evidence_trace:
            if row["domain_id"] == domain_id:
                row["domain_score_contribution"] = round(final_domain, 4)

    g0_fail = any(not r["admissible"] for r in artifact_results)
    g1_fail = any(d["must_have"] and d["final_domain_score"] < 3.0 for d in domain_scores)
    g2_fail = any(not t["evidence_artifact_ids"] for t in task_scores)

    gate_results = [
        {
            "gate_id": "G0_INTEGRITY",
            "status": "FAIL" if g0_fail else "PASS",
            "blocking": g0_fail,
            "reason_codes": ["ARTIFACT_INTEGRITY_FAILURE"] if g0_fail else [],
            "affected_artifact_ids": [r["artifact_id"] for r in artifact_results if not r["admissible"]],
        },
        {
            "gate_id": "G1_MINIMUM_READINESS",
            "status": "FAIL" if g1_fail else "PASS",
            "blocking": g1_fail,
            "reason_codes": ["MUST_HAVE_DOMAIN_BELOW_THRESHOLD"] if g1_fail else [],
            "affected_artifact_ids": [],
        },
        {
            "gate_id": "G2_EVIDENCE_SUFFICIENCY",
            "status": "FAIL" if g2_fail else "PASS",
            "blocking": g2_fail,
            "reason_codes": ["INSUFFICIENT_TASK_EVIDENCE"] if g2_fail else [],
            "affected_artifact_ids": [],
        },
    ]

    composite = round(sum(d["final_domain_score"] for d in domain_scores) / max(1, len(domain_scores)), 4)
    if any(g["blocking"] for g in gate_results):
        label = "NOT_READY"
        status = "FAIL"
    elif composite >= 4.0:
        label = "READY_HIGH_CONFIDENCE"
        status = "PASS"
    elif composite >= 3.0:
        label = "READY_WITH_EVIDENCE"
        status = "PASS"
    else:
        label = "PARTIAL_READINESS"
        status = "PASS"

    ts = str(bundle.get("evaluation_timestamp") or "1970-01-01T00:00:00Z")
    protocol_version = "2026.2"
    final_classification = {
        "status": status,
        "classification_label": label,
        "composite_score": composite,
        "integrity_hash": "0" * 64,
    }

    chain, terminal = _build_chain(
        bundle=bundle,
        ts=ts,
        protocol_version=protocol_version,
        artifact_results=artifact_results,
        admissible_ids=admissible_ids,
        id_to_artifact=id_to_artifact,
        task_scores=task_scores,
        domain_scores=domain_scores,
        gate_results=gate_results,
        final_classification=final_classification,
        evidence_trace=evidence_trace,
    )

    final_classification["integrity_hash"] = terminal
    result = {
        "protocol_metadata": {
            "protocol_id": "GPT5.4-AUDIT-HARDENING-PROTOCOL-2026",
            "protocol_version": protocol_version,
            "target_protocol_id": bundle["target_protocol_id"],
            "execution_mode": bundle["execution_mode"],
            "evaluation_timestamp": ts,
            "model_identifier": bundle["model_identifier"],
            "artifact_count": len(bundle["artifacts"]),
            "evaluation_hash": terminal,
        },
        "artifact_validation_results": artifact_results,
        "task_scores": task_scores,
        "domain_scores": domain_scores,
        "gate_results": gate_results,
        "final_classification": final_classification,
        "execution_chain_format_version": CHAIN_FORMAT_VERSION,
        "execution_state_chain": chain,
        "execution_chain_terminal_hash": terminal,
        "evidence_trace_table": evidence_trace,
    }

    ok, err = validate(result, "evaluation-result.schema.json")
    if not ok:
        raise SystemExit(f"EvaluationResult schema validation failed: {err}")
    if result["execution_chain_terminal_hash"] != result["protocol_metadata"]["evaluation_hash"]:
        raise SystemExit("TERMINAL_CHAIN_MISMATCH")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_bundle_json")
    parser.add_argument("--output", required=False)
    parser.add_argument("--allow-non-authoritative-git", action="store_true")
    args = parser.parse_args()

    assert_git_authoritative(allow_non_authoritative_git=args.allow_non_authoritative_git)
    bundle = load_json(Path(args.input_bundle_json))
    ok, err = validate(bundle, "reference-input-bundle.schema.json")
    if not ok:
        raise SystemExit(f"Input bundle validation failed: {err}")
    result = compute(bundle)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
