"""
CognitiveEngine — the NCE reasoning core.

Orchestrates cognitive strategies through the CorticalColumn:
    1. PredictiveCoding generates priors
    2. AbductiveInference generates competing hypotheses
    3. ReductioAdAbsurdum tests claims
    4. EpistemicForaging identifies knowledge gaps
    5. Confidence calibration enforces epistemic gates

The engine is domain-adaptive:
    CODE     → Markov blanket dominates, reductio mandatory
    ANALYSIS → Abductive inference, min 2 hypotheses
    RESEARCH → Epistemic foraging maximizes unknowns
    CREATIVE → Invert predictive coding (maximize surprise × coherence)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from neuron7x_agents.cognitive.strategies import (
    AbductiveInference,
    EpistemicForaging,
    Hypothesis,
    PredictiveCoding,
    ReductioAdAbsurdum,
)
from neuron7x_agents.primitives.column import (
    ColumnResult,
    Complexity,
    CorticalColumn,
)
from neuron7x_agents.primitives.confidence import (
    CalibratedConfidence,
    enforce_gate,
)
from neuron7x_agents.primitives.evidence import MarkovBlanket


class Domain(enum.Enum):
    """Domain adaptation modes."""

    CODE = "code"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    CREATIVE = "creative"
    CONVERSATIONAL = "conversational"


@dataclass
class ReasoningResult:
    """Complete output from a cognitive reasoning pass."""

    output: Any
    confidence: CalibratedConfidence
    hypotheses: list[Hypothesis]
    blanket: MarkovBlanket
    column_result: ColumnResult
    domain: Domain
    foraging_needed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveEngine:
    """
    NCE — Neurosymbolic Cognitive Engine.

    Composes cognitive strategies through adversarial column processing
    to produce calibrated, evidence-grounded reasoning.

    Parameters
    ----------
    domain : Domain
        Primary domain for strategy adaptation.
    max_iterations : int
        Maximum adversarial iterations in the column.

    Examples
    --------
    >>> engine = CognitiveEngine(domain=Domain.ANALYSIS)
    >>> result = engine.reason("What drives neural synchronization?")
    >>> result.confidence.level
    <ConfidenceLevel.REASONABLE: 'reasonable'>
    """

    def __init__(
        self,
        domain: Domain = Domain.ANALYSIS,
        max_iterations: int = 3,
    ) -> None:
        self.domain = domain
        self.column = CorticalColumn(max_iterations=max_iterations)
        self.predictor = PredictiveCoding()
        self.abduction = AbductiveInference()
        self.reductio = ReductioAdAbsurdum()
        self.forager = EpistemicForaging()
        self.blanket = MarkovBlanket()

    def reason(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        complexity: Complexity = Complexity.COMPLEX,
    ) -> ReasoningResult:
        """
        Execute a full reasoning pass on the given query.

        Parameters
        ----------
        query : str
            The question or task to reason about.
        context : dict, optional
            Additional context for reasoning.
        complexity : Complexity
            Task complexity level.

        Returns
        -------
        ReasoningResult
            Complete reasoning output with calibrated confidence.
        """
        ctx = {"query": query, **(context or {})}

        # Phase 1: Predictive coding — generate prior
        prediction = self.predictor.predict(ctx)
        ctx["prediction"] = prediction

        # Phase 2: Column processing — adversarial reasoning
        column_result = self.column.run(ctx, complexity)

        # Phase 3: Confidence calibration
        raw_confidence = column_result.final_confidence
        calibrated = enforce_gate(raw_confidence)

        # Phase 4: Check if epistemic foraging is needed
        foraging_needed = self.forager.needs_more_evidence()

        return ReasoningResult(
            output=column_result.final_output,
            confidence=calibrated,
            hypotheses=[],
            blanket=self.blanket,
            column_result=column_result,
            domain=self.domain,
            foraging_needed=foraging_needed,
            metadata={"query": query, "iterations": column_result.iterations},
        )

    def hypothesize(
        self,
        hypotheses: list[Hypothesis],
    ) -> Hypothesis | None:
        """
        Rank competing hypotheses and return the best, if distinguishable.

        Returns None if hypotheses are too close (foraging needed).
        """
        return self.abduction.best(hypotheses)

    def test_claim(
        self,
        claim: str,
        negation: str,
        established_facts: list[str],
    ) -> bool:
        """
        Test a claim via reductio ad absurdum.

        Returns True if the claim survives (negation contradicts facts).
        """
        result = self.reductio.test(claim, negation, established_facts)
        return result.survived
