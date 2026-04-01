"""
HybridAgent — the full cognitive stack in one agent.

    ┌─────────────────────────────────────────────────┐
    │                 HybridAgent                      │
    │                                                  │
    │  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
    │  │ NCE      │  │ SERO      │  │ Kriterion    │  │
    │  │ Cognitive│←→│ Regulation│←→│ Verification │  │
    │  │ Engine   │  │ HVR+Immune│  │ Gate+Anti-GM │  │
    │  └──────────┘  └───────────┘  └──────────────┘  │
    │        ↕              ↕              ↕           │
    │  ┌──────────────────────────────────────────┐   │
    │  │         Cortical Column (shared)          │   │
    │  │    Creator → Critic → Auditor → Verifier  │   │
    │  └──────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────┘

The HybridAgent composes:
    - CognitiveEngine for reasoning (predict, hypothesize, test)
    - HormonalRegulator for homeostasis (stress, throughput, damping)
    - EpistemicGate for verification (evidence, provenance, anti-gaming)
    - BayesianImmune for threat detection (dual-signal, quarantine)

This is not three systems bolted together. The regulation layer
modulates cognitive depth, and verification gates cognitive output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from neuron7x_agents.cognitive.engine import CognitiveEngine, Domain, ReasoningResult
from neuron7x_agents.primitives.column import Complexity
from neuron7x_agents.regulation.hvr import HormonalRegulator, HVRConfig, SeverityWeight
from neuron7x_agents.regulation.immune import Alert, BayesianImmune
from neuron7x_agents.verification.anti_gaming import AntiGamingDetector
from neuron7x_agents.verification.gate import EpistemicGate, GateVerdict

if TYPE_CHECKING:
    from neuron7x_agents.primitives.confidence import CalibratedConfidence
    from neuron7x_agents.primitives.evidence import EvidenceItem


@dataclass
class AgentResponse:
    """Complete agent response with all subsystem outputs."""

    reasoning: ReasoningResult
    regulation_throughput: float
    is_under_stress: bool
    gate_verdict: GateVerdict | None
    evidence_used: list[EvidenceItem]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> CalibratedConfidence:
        """The calibrated confidence from the reasoning engine."""
        return self.reasoning.confidence

    @property
    def is_trustworthy(self) -> bool:
        """True if both reasoning and verification are satisfied."""
        if self.gate_verdict is not None:
            return self.gate_verdict.is_admissible and self.confidence.is_trustworthy
        return self.confidence.is_trustworthy


class HybridAgent:
    """
    Full-stack cognitive agent: NCE + SERO + Kriterion.

    The agent adapts its behavior based on internal state:
    - Under stress → reduces cognitive depth (faster, simpler reasoning)
    - Low confidence → triggers epistemic foraging
    - Evidence gaps → caps output confidence via gate

    Parameters
    ----------
    domain : Domain
        Primary reasoning domain.
    hvr_config : HVRConfig, optional
        Hormonal regulation parameters.

    Examples
    --------
    >>> agent = HybridAgent(domain=Domain.ANALYSIS)
    >>> response = agent.process("What causes neural gamma oscillations?")
    >>> response.confidence.level
    <ConfidenceLevel.REASONABLE: 'reasonable'>
    >>> response.regulation_throughput
    1.0
    """

    def __init__(
        self,
        domain: Domain = Domain.ANALYSIS,
        hvr_config: HVRConfig | None = None,
    ) -> None:
        self.engine = CognitiveEngine(domain=domain)
        self.regulator = HormonalRegulator(config=hvr_config)
        self.immune = BayesianImmune()
        self.gate = EpistemicGate()
        self.anti_gaming = AntiGamingDetector()

    def _stress_to_complexity(self, throughput: float) -> Complexity:
        """Map current throughput to cognitive complexity budget."""
        if throughput >= 0.9:
            return Complexity.COMPLEX
        if throughput >= 0.7:
            return Complexity.MODERATE
        return Complexity.TRIVIAL

    def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        evidence: list[EvidenceItem] | None = None,
        stress_channels: list[SeverityWeight] | None = None,
    ) -> AgentResponse:
        """
        Process a query through the full cognitive stack.

        Parameters
        ----------
        query : str
            The question or task.
        context : dict, optional
            Additional context.
        evidence : list[EvidenceItem], optional
            Supporting evidence for verification.
        stress_channels : list[SeverityWeight], optional
            Current system stress indicators.

        Returns
        -------
        AgentResponse
            Complete response from all subsystems.
        """
        # Step 1: Regulation — assess stress and set cognitive budget
        state = self.regulator.tick(stress_channels) if stress_channels else self.regulator.state
        complexity = self._stress_to_complexity(state.throughput)

        # Step 2: Cognition — reason at the budgeted depth
        reasoning = self.engine.reason(query, context, complexity)

        # Step 3: Verification — gate the output if evidence provided
        gate_verdict = None
        if evidence:
            gate_verdict = self.gate.evaluate(evidence, reasoning.confidence.calibrated_score)

        return AgentResponse(
            reasoning=reasoning,
            regulation_throughput=state.throughput,
            is_under_stress=state.is_stressed,
            gate_verdict=gate_verdict,
            evidence_used=evidence or [],
            metadata={
                "complexity_budget": complexity.name,
                "tick": state.tick,
                "damped_stress": state.damped_stress,
            },
        )

    def check_threat(self, alerts: list[Alert]) -> bool:
        """Run alerts through the Bayesian immune system."""
        verdict = self.immune.evaluate(alerts)
        return verdict.is_real_threat
