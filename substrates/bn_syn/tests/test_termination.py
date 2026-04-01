from aoc.contracts import AuditResult, InnovationBand, SigmaIndex
from aoc.termination import TerminationOracle


def _audit(passed: bool, critical: bool = False) -> AuditResult:
    return AuditResult(
        passed=passed,
        confidence=1.0 if passed else 0.3,
        critical_failure=critical,
        reasons=["x"],
        checks={"c": {"required": True, "passed": passed}},
    )


def test_no_success_when_delta_exceeds_band() -> None:
    d = TerminationOracle().evaluate(
        iteration=1,
        max_iterations=5,
        delta=0.9,
        band=InnovationBand(0.1, 0.5),
        sigma=SigmaIndex(0.1, 0.1, 0.1, 0.9),
        audit=_audit(True),
        audit_verified=True,
        coherence_threshold=0.8,
        invariants_ok=True,
    )
    assert d.status != "PASS"


def test_critical_failure_halts_immediately() -> None:
    d = TerminationOracle().evaluate(
        iteration=1,
        max_iterations=5,
        delta=0.2,
        band=InnovationBand(0.1, 0.5),
        sigma=SigmaIndex(0.1, 0.1, 0.1, 0.9),
        audit=_audit(False, critical=True),
        audit_verified=False,
        coherence_threshold=0.8,
        invariants_ok=True,
    )
    assert d.status == "FAIL"


def test_no_stop_when_audit_failed() -> None:
    d = TerminationOracle().evaluate(
        iteration=1,
        max_iterations=5,
        delta=0.2,
        band=InnovationBand(0.0, 0.5),
        sigma=SigmaIndex(0.1, 0.1, 0.1, 0.9),
        audit=_audit(False),
        audit_verified=False,
        coherence_threshold=0.8,
        invariants_ok=True,
    )
    assert d.status != "PASS"


def test_pass_on_last_allowed_iteration() -> None:
    d = TerminationOracle().evaluate(
        iteration=1,
        max_iterations=1,
        delta=0.2,
        band=InnovationBand(0.0, 0.5),
        sigma=SigmaIndex(0.1, 0.1, 0.1, 0.9),
        audit=_audit(True),
        audit_verified=True,
        coherence_threshold=0.8,
        invariants_ok=True,
    )
    assert d.status == "PASS"
