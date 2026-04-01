import json
from pathlib import Path

from aoc.contracts import VerificationResult, load_task_contract
from aoc.controller import AOCController

from tests.fixtures import LocalCrossModelAuditorStub


REQUIRED = {
    "final_artifact.md",
    "zeropoint.json",
    "run_summary.json",
    "sigma_trace.json",
    "delta_trace.json",
    "audit_trace.json",
    "auditor_reliability_trace.json",
    "termination_verdict.json",
}


def test_full_controller_run_and_determinism(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(__import__("yaml").safe_load(Path("examples/basic_task.yaml").read_text())))
    payload["output"]["artifact_filename"] = "final_artifact.md"
    c = load_task_contract(payload)

    out = tmp_path / "run"
    v1 = AOCController(c, out).run()
    files = {p.name for p in out.iterdir()}
    assert REQUIRED.issubset(files)
    assert (out / "evidence_bundle").is_dir()
    assert v1["status"] == "PASS"
    assert v1["audit_reliability_status"] == "reliable_audit"

    v2 = AOCController(c, out).run()
    assert v1 == v2


class RejectPassingVerdictVerifier:
    def verify(self, *, content: str, contract: object, audit: object, iteration: int) -> VerificationResult:
        return VerificationResult(
            verification_status="verified_rejected",
            verifier_passed=False,
            ground_truth=False,
            basis={"provider": "reject_passing_verdict", "iteration": iteration},
            latency_iters=1,
        )


def test_primary_pass_can_be_rejected_by_verifier(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(__import__("yaml").safe_load(Path("examples/basic_task.yaml").read_text())))
    payload["output"]["artifact_filename"] = "final_artifact.md"
    payload["auditor"]["verifier_kind"] = ""
    contract = load_task_contract(payload)

    out = tmp_path / "rejected"
    verdict = AOCController(
        contract,
        out,
        primary_auditor=LocalCrossModelAuditorStub(),
        verifier=RejectPassingVerdictVerifier(),
    ).run()

    assert verdict["status"] != "PASS"
    assert verdict["audit_reliability_status"] == "rejected_by_verifier"

    audit_trace = json.loads((out / "audit_trace.json").read_text())
    assert audit_trace["trace"][0]["primary_audit"]["passed"] is True
    assert audit_trace["trace"][0]["verification"]["verification_status"] == "verified_rejected"

    reliability = json.loads((out / "auditor_reliability_trace.json").read_text())
    assert reliability["verification_status"] == "rejected_by_verifier"
    assert reliability["metrics_status"] == "verified"
    assert reliability["false_conservation_rate"] == 1.0


def test_run_without_verifier_stays_unverified(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(__import__("yaml").safe_load(Path("examples/basic_task.yaml").read_text())))
    payload["output"]["artifact_filename"] = "final_artifact.md"
    payload["auditor"]["verifier_kind"] = ""
    contract = load_task_contract(payload)

    verdict = AOCController(contract, tmp_path / "unverified").run()

    assert verdict["status"] != "PASS"
    assert verdict["audit_reliability_status"] == "unverified"
    reliability = json.loads((tmp_path / "unverified" / "auditor_reliability_trace.json").read_text())
    assert reliability["metrics_status"] == "unverified"
