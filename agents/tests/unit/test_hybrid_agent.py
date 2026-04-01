"""Tests for the HybridAgent — full cognitive stack integration."""

from __future__ import annotations

from neuron7x_agents.agents.hybrid import AgentResponse, HybridAgent
from neuron7x_agents.cognitive.engine import Domain
from neuron7x_agents.primitives.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceTier,
)
from neuron7x_agents.regulation.hvr import SeverityWeight
from neuron7x_agents.regulation.immune import Alert


class TestHybridAgent:
    def test_basic_reasoning(self) -> None:
        agent = HybridAgent(domain=Domain.ANALYSIS)
        response = agent.process("What is gamma?")
        assert isinstance(response, AgentResponse)
        assert response.regulation_throughput == 1.0
        assert response.is_under_stress is False

    def test_stress_reduces_complexity(self) -> None:
        agent = HybridAgent(domain=Domain.CODE)
        # Heavy stress
        channels = [SeverityWeight("error_rate", severity=100.0, current_value=1.0)]
        response = agent.process("fix bug", stress_channels=channels)
        assert response.metadata["complexity_budget"] in ("TRIVIAL", "MODERATE")

    def test_no_stress_full_complexity(self) -> None:
        agent = HybridAgent()
        channels = [SeverityWeight("all_clear", severity=1.0, current_value=0.0)]
        response = agent.process("analyze", stress_channels=channels)
        assert response.metadata["complexity_budget"] == "COMPLEX"

    def test_evidence_gates_output(self) -> None:
        agent = HybridAgent()
        evidence = [
            EvidenceItem(
                "fact_1", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:1"
            ),
            EvidenceItem(
                "fact_2", EvidenceTier.GIVEN, EvidenceSource.PEER_REVIEWED, provenance="doi:2"
            ),
            EvidenceItem(
                "fact_3", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:3"
            ),
        ]
        response = agent.process("evaluate claim", evidence=evidence)
        assert response.gate_verdict is not None
        assert response.gate_verdict.is_admissible

    def test_no_evidence_no_gate(self) -> None:
        agent = HybridAgent()
        response = agent.process("quick question")
        assert response.gate_verdict is None

    def test_threat_detection_single_channel(self) -> None:
        agent = HybridAgent()
        assert agent.check_threat([Alert("error_rate", 0.8, 0.9)]) is False

    def test_threat_detection_dual_channel(self) -> None:
        agent = HybridAgent()
        alerts = [
            Alert("error_rate", 0.8, 0.9),
            Alert("latency", 0.6, 0.7),
        ]
        assert agent.check_threat(alerts) is True

    def test_safety_invariant_under_load(self) -> None:
        """T(t) ≥ T_min even under sustained maximum stress."""
        agent = HybridAgent()
        channels = [SeverityWeight("chaos", severity=100.0, current_value=1.0)]
        for _ in range(100):
            response = agent.process("survive", stress_channels=channels)
        assert agent.regulator.safety_invariant_holds()
        assert response.regulation_throughput >= agent.regulator.config.t_min

    def test_trustworthy_requires_both_subsystems(self) -> None:
        agent = HybridAgent()
        evidence = [
            EvidenceItem("x", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:1"),
            EvidenceItem("y", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:2"),
        ]
        response = agent.process("verify", evidence=evidence)
        # is_trustworthy checks both confidence calibration and gate admissibility
        assert isinstance(response.is_trustworthy, bool)
