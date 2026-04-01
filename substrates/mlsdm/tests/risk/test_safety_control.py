from mlsdm.risk.safety_control import (
    RiskAssessment,
    RiskContractAdapter,
    RiskDirective,
    RiskInputSignals,
    RiskMode,
)


def test_risk_contract_adapter_builds_risk_signal_from_flags() -> None:
    signals = RiskInputSignals(
        security_flags=("policy_violation",),
        cognition_risk_score=0.2,
        observability_anomaly_score=0.8,
        metadata={"request_id": "req-1"},
    )

    risk_signal = RiskContractAdapter.risk_signal(signals)

    assert risk_signal.threat == 1.0
    assert risk_signal.risk == 0.8
    assert risk_signal.source == "safety_control"
    assert risk_signal.metadata["security_flag_count"] == 1


def test_risk_contract_adapter_uses_anomaly_score_without_flags() -> None:
    signals = RiskInputSignals(
        security_flags=(),
        cognition_risk_score=0.3,
        observability_anomaly_score=0.6,
    )

    risk_signal = RiskContractAdapter.risk_signal(signals)

    assert risk_signal.threat == 0.6
    assert risk_signal.risk == 0.6


def test_risk_contract_adapter_builds_action_gating_signal() -> None:
    assessment = RiskAssessment(
        composite_score=0.75,
        mode=RiskMode.DEGRADED,
        reasons=("cognition_high_risk",),
        evidence={},
    )
    directive = RiskDirective(
        mode=RiskMode.DEGRADED,
        allow_execution=True,
        degrade_actions=("token_cap",),
        emergency_fallback=None,
        audit_tags=("risk_degraded",),
    )

    gating_signal = RiskContractAdapter.action_gating_signal(assessment, directive)

    assert gating_signal.allow is True
    assert gating_signal.reason == "cognition_high_risk"
    assert gating_signal.mode == "degraded"
    assert gating_signal.metadata["degraded"] is True
    assert gating_signal.metadata["emergency"] is False
    assert gating_signal.metadata["audit_tags"] == "risk_degraded"


def test_risk_contract_adapter_falls_back_to_mode_for_reason() -> None:
    assessment = RiskAssessment(
        composite_score=0.2,
        mode=RiskMode.NORMAL,
        reasons=(),
        evidence={},
    )
    directive = RiskDirective(
        mode=RiskMode.NORMAL,
        allow_execution=True,
        degrade_actions=(),
        emergency_fallback=None,
        audit_tags=(),
    )

    gating_signal = RiskContractAdapter.action_gating_signal(assessment, directive)

    assert gating_signal.reason == "normal"
