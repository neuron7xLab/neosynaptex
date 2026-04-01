from mlsdm.protocols.neuro_signals import RiskSignal


def test_risk_signal_metadata_is_isolated_per_instance() -> None:
    first = RiskSignal(threat=0.1, risk=0.2, source="unit")
    second = RiskSignal(threat=0.3, risk=0.4, source="unit")

    first.metadata["note"] = "alpha"

    assert "note" not in second.metadata


def test_risk_signal_metadata_preserves_types() -> None:
    signal = RiskSignal(
        threat=0.4,
        risk=0.5,
        source="unit",
        metadata={"count": 3, "flag": True, "note": "ok"},
    )

    assert signal.metadata == {"count": 3, "flag": True, "note": "ok"}
