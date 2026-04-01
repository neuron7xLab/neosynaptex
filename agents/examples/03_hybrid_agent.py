#!/usr/bin/env python3
"""
HybridAgent — the full cognitive stack in action.

Demonstrates how NCE reasoning, SERO regulation, and Kriterion
verification compose into a single agent that adapts its behavior
based on internal state.

Usage:
    python examples/03_hybrid_agent.py
"""

from neuron7x_agents.agents.hybrid import HybridAgent
from neuron7x_agents.cognitive.engine import Domain
from neuron7x_agents.primitives.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceTier,
)
from neuron7x_agents.regulation.hvr import SeverityWeight
from neuron7x_agents.regulation.immune import Alert


def main() -> None:
    print("=" * 60)
    print("HYBRID AGENT — NCE + SERO + KRITERION")
    print("=" * 60)

    agent = HybridAgent(domain=Domain.ANALYSIS)

    # Scenario 1: Normal operation
    print("\n--- Scenario 1: Normal operation (no stress) ---")
    response = agent.process(
        "What drives gamma oscillations in cortical circuits?",
        evidence=[
            EvidenceItem(
                "PV+ interneurons generate gamma via PING",
                EvidenceTier.GIVEN,
                EvidenceSource.PEER_REVIEWED,
                provenance="doi:10.1038/nn.2156",
            ),
            EvidenceItem(
                "Gamma power correlates with cognitive load",
                EvidenceTier.GIVEN,
                EvidenceSource.EXPERIMENT,
                provenance="doi:10.1016/j.neuron.2009.06.016",
            ),
        ],
    )
    print(f"  Throughput:  {response.regulation_throughput:.2f}")
    print(f"  Stressed:    {response.is_under_stress}")
    print(f"  Confidence:  {response.confidence.level.value}")
    print(f"  Gate status: {response.gate_verdict.status.value}")
    print(f"  Trustworthy: {response.is_trustworthy}")
    print(f"  Complexity:  {response.metadata['complexity_budget']}")

    # Scenario 2: Under heavy stress
    print("\n--- Scenario 2: Under heavy stress ---")
    stress_channels = [
        SeverityWeight("error_rate", severity=100.0, current_value=0.8),
        SeverityWeight("cpu", severity=10.0, current_value=0.95),
        SeverityWeight("queue", severity=5.0, current_value=0.9),
    ]
    response = agent.process(
        "Diagnose service degradation",
        stress_channels=stress_channels,
    )
    print(f"  Throughput:  {response.regulation_throughput:.4f}")
    print(f"  Stressed:    {response.is_under_stress}")
    print(f"  Complexity:  {response.metadata['complexity_budget']}")
    print(f"  → Stress reduces cognitive depth automatically.")

    # Scenario 3: Threat detection
    print("\n--- Scenario 3: Bayesian immune — threat detection ---")

    # Single channel → quarantined
    single = agent.check_threat([Alert("error_rate", 0.8, 0.9)])
    print(f"  Single channel alert: real_threat={single}")

    # Dual channel → real threat
    dual = agent.check_threat([
        Alert("error_rate", 0.8, 0.9),
        Alert("latency", 0.7, 0.8),
    ])
    print(f"  Dual channel alert:   real_threat={dual}")
    print(f"  → Dual-signal detection: 12x reduction in false positives.")

    # Scenario 4: Safety invariant under sustained chaos
    print("\n--- Scenario 4: Safety invariant under 100 ticks of max stress ---")
    chaos_agent = HybridAgent()
    chaos_channels = [SeverityWeight("chaos", severity=100.0, current_value=1.0)]
    for _ in range(100):
        chaos_agent.process("survive", stress_channels=chaos_channels)
    holds = chaos_agent.regulator.safety_invariant_holds()
    t_min = chaos_agent.regulator.config.t_min
    t_final = chaos_agent.regulator.state.throughput
    print(f"  T_min:            {t_min}")
    print(f"  Final throughput: {t_final:.4f}")
    print(f"  Invariant holds:  {holds}")
    print(f"  → T(t) >= T_min guaranteed by construction (Eq.4).")


if __name__ == "__main__":
    main()
