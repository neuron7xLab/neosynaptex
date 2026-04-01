"""Tests for deterministic response-quality gating."""

from mlsdm.core.response_quality import ResponseQualityGate


def test_quality_gate_detects_collapse() -> None:
    gate = ResponseQualityGate()
    decision = gate.evaluate(prompt="test", response="   ", confidence=0.9)
    assert decision.action == "reject"
    assert "collapse" in decision.triggered_modes


def test_quality_gate_detects_looping() -> None:
    gate = ResponseQualityGate()
    response = "repeat repeat repeat repeat repeat repeat repeat repeat\n" * 3
    decision = gate.evaluate(prompt="loop test", response=response, confidence=0.9)
    assert decision.action == "reject"
    assert "looping" in decision.triggered_modes


def test_quality_gate_detects_telegraphing() -> None:
    gate = ResponseQualityGate()
    response = "Need fix. Patch now. Send update. Ship fast. Avoid delay. Push build today."
    decision = gate.evaluate(prompt="status update", response=response, confidence=0.9)
    assert decision.action == "degrade"
    assert "telegraphing" in decision.triggered_modes


def test_quality_gate_detects_incoherence() -> None:
    gate = ResponseQualityGate()
    response = "1234 5678 91011 1213 1415 1617 1819 2021 2223 2425 2627 2829"
    decision = gate.evaluate(prompt="coherence", response=response, confidence=0.9)
    assert decision.action == "reject"
    assert "incoherence" in decision.triggered_modes


def test_quality_gate_detects_drift() -> None:
    gate = ResponseQualityGate()
    prompt = "database connection timeout retry logic"
    response = (
        "Weather patterns are shifting rapidly across the coast with strong winds "
        "and varying humidity levels that impact seasonal trends significantly."
    )
    decision = gate.evaluate(prompt=prompt, response=response, confidence=0.9)
    assert decision.action == "degrade"
    assert "drift" in decision.triggered_modes


def test_quality_gate_detects_hallucination_confidence() -> None:
    gate = ResponseQualityGate()
    response = (
        "I think this might be accurate, maybe. I am not sure, perhaps it could be wrong."
    )
    decision = gate.evaluate(prompt="facts", response=response, confidence=0.2)
    assert decision.action == "degrade"
    assert "hallucination" in decision.triggered_modes
