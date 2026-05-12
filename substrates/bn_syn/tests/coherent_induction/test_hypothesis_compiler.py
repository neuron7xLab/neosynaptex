from coherent_induction.hypothesis_compiler import ClaimStatus, compile_hypothesis


def test_compiler_requires_falsifier_and_artifact() -> None:
    frame = compile_hypothesis("x", ClaimStatus.TESTABLE_MODEL, "artifact.md", "falsify if no benchmark delta")
    assert frame.claim_status == ClaimStatus.TESTABLE_MODEL
