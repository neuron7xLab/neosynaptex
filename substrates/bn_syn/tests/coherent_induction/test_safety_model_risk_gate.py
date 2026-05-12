from coherent_induction.safety_model_risk_gate import safety_gate


def test_safety_gate_blocks_unbounded_claim() -> None:
    ok, _ = safety_gate("literal fusion")
    assert not ok


def test_safety_gate_blocks_obfuscated_claim_spacing() -> None:
    ok, reason = safety_gate("Literal---Fusion")
    assert not ok
    assert "literal" in reason


def test_safety_gate_fails_closed_on_empty_input() -> None:
    ok, reason = safety_gate("   ")
    assert not ok
    assert reason == "blocked: empty_claim"


def test_safety_gate_blocks_unbenchmarked_superiority_claim() -> None:
    ok, reason = safety_gate("Our method is 10x better than baseline.")
    assert not ok
    assert reason == "blocked: unbenchmarked_superiority_claim"


def test_safety_gate_allows_superiority_claim_with_benchmark_context() -> None:
    ok, reason = safety_gate("10x better per benchmark jsonl with confidence interval")
    assert ok
    assert reason == "safe"
