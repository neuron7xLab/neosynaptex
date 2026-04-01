"""
Cognitive strategies — executable reasoning primitives.

Each strategy maps to a known cognitive/neuroscience mechanism:

    PredictiveCoding    — predict → observe → update (Friston free energy)
    AbductiveInference  — generate competing hypotheses, rank by parsimony
    ReductioAdAbsurdum  — assume negation, seek contradiction
    EpistemicForaging   — "what don't I know that would change this?"

These are composable: a complex reasoning task chains multiple strategies
through the CorticalColumn adversarial loop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
#  Predictive Coding
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Prediction:
    """A prediction with its prior probability."""

    content: Any
    prior: float  # 0.0-1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionError:
    """Mismatch between prediction and observation."""

    prediction: Prediction
    observation: Any
    error_magnitude: float  # 0.0 = perfect match, 1.0 = total mismatch
    triggers_abduction: bool = False  # large error → abductive inference


class PredictiveCoding:
    """
    Predict → Observe → Compute Error → Update.

    Large prediction errors trigger abductive inference (hypothesis
    generation) rather than simple Bayesian update.

    Parameters
    ----------
    abduction_threshold : float
        Error magnitude above which abductive inference is triggered.
    """

    def __init__(self, abduction_threshold: float = 0.5) -> None:
        self.abduction_threshold = abduction_threshold
        self._history: list[PredictionError] = []

    def predict(self, context: dict[str, Any], prior: float = 0.5) -> Prediction:
        """Generate a prediction from context with prior probability."""
        return Prediction(
            content=context.get("expected_outcome"),
            prior=max(0.0, min(1.0, prior)),
            metadata={"context_keys": list(context.keys())},
        )

    def observe(self, prediction: Prediction, observation: Any) -> PredictionError:
        """Compare prediction to observation and compute error."""
        if prediction.content == observation:
            magnitude = 0.0
        elif prediction.content is None or observation is None:
            magnitude = 1.0
        else:
            magnitude = 1.0 - prediction.prior

        error = PredictionError(
            prediction=prediction,
            observation=observation,
            error_magnitude=magnitude,
            triggers_abduction=magnitude >= self.abduction_threshold,
        )
        self._history.append(error)
        return error

    @property
    def cumulative_surprise(self) -> float:
        """Total prediction error accumulated (information-theoretic surprise)."""
        if not self._history:
            return 0.0
        return sum(-math.log(max(1e-10, 1.0 - e.error_magnitude)) for e in self._history)


# ═══════════════════════════════════════════════════════════════════════
#  Abductive Inference
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Hypothesis:
    """A competing hypothesis with parsimony and falsifiability scores."""

    description: str
    parsimony: float  # 0.0-1.0, higher = simpler
    falsifiability: float  # 0.0-1.0, higher = more testable
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Combined score: parsimony × falsifiability, penalized by contradictions."""
        base = self.parsimony * self.falsifiability
        penalty = len(self.contradicting_evidence) * 0.1
        return max(0.0, base - penalty)


class AbductiveInference:
    """
    Generate competing hypotheses, rank by parsimony + falsifiability.

    Minimum 2 hypotheses required. If margin between top two is < 0.2,
    epistemic foraging is triggered (need more evidence).

    Parameters
    ----------
    min_hypotheses : int
        Minimum number of hypotheses to generate.
    foraging_margin : float
        Margin below which epistemic foraging is needed.
    """

    def __init__(
        self,
        min_hypotheses: int = 2,
        foraging_margin: float = 0.2,
    ) -> None:
        self.min_hypotheses = min_hypotheses
        self.foraging_margin = foraging_margin

    def rank(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        """Rank hypotheses by score, highest first."""
        return sorted(hypotheses, key=lambda h: h.score, reverse=True)

    def needs_foraging(self, hypotheses: list[Hypothesis]) -> bool:
        """True if top two hypotheses are too close to distinguish."""
        ranked = self.rank(hypotheses)
        if len(ranked) < 2:
            return True
        return (ranked[0].score - ranked[1].score) < self.foraging_margin

    def best(self, hypotheses: list[Hypothesis]) -> Hypothesis | None:
        """Return the best hypothesis, or None if insufficient evidence."""
        if len(hypotheses) < self.min_hypotheses:
            return None
        ranked = self.rank(hypotheses)
        if self.needs_foraging(hypotheses):
            return None  # Not enough separation
        return ranked[0]


# ═══════════════════════════════════════════════════════════════════════
#  Reductio ad Absurdum
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ReductioResult:
    """Result of assuming a negation and seeking contradictions."""

    original_claim: str
    negation: str
    contradictions_found: list[str]
    survived: bool  # True if the original claim survived reductio

    @property
    def strength(self) -> float:
        """How strongly the reductio supports the original claim."""
        if not self.survived:
            return 0.0
        return min(1.0, len(self.contradictions_found) * 0.25)


class ReductioAdAbsurdum:
    """
    Assume the negation of a claim, seek contradictions.

    If contradictions are found with established facts, the original
    claim is strengthened. If no contradictions are found, the claim
    may need revision.
    """

    def test(
        self,
        claim: str,
        negation: str,
        established_facts: list[str],
    ) -> ReductioResult:
        """
        Test a claim via reductio ad absurdum.

        Parameters
        ----------
        claim : str
            The claim to test.
        negation : str
            The negation of the claim.
        established_facts : list[str]
            Known facts to check for contradictions.

        Returns
        -------
        ReductioResult
            Whether the claim survived and what contradictions were found.
        """
        contradictions = [fact for fact in established_facts if self._contradicts(negation, fact)]
        return ReductioResult(
            original_claim=claim,
            negation=negation,
            contradictions_found=contradictions,
            survived=len(contradictions) > 0,
        )

    @staticmethod
    def _contradicts(negation: str, fact: str) -> bool:
        """Check if a negation contradicts an established fact."""
        neg_lower = negation.lower()
        fact_lower = fact.lower()
        neg_tokens = set(neg_lower.split())
        fact_tokens = set(fact_lower.split())
        overlap = neg_tokens & fact_tokens
        return len(overlap) >= max(2, len(fact_tokens) // 3)


# ═══════════════════════════════════════════════════════════════════════
#  Epistemic Foraging
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ForagingQuestion:
    """A question that would most change the current answer."""

    question: str
    expected_impact: float  # 0.0-1.0, how much the answer could change
    domain: str = ""


class EpistemicForaging:
    """
    "What do I NOT know that would most change this answer?"

    Generates the highest-impact questions that could shift confidence.
    This is the meta-cognitive layer: reasoning about what to reason about.
    """

    def __init__(self, impact_threshold: float = 0.2) -> None:
        self.impact_threshold = impact_threshold
        self._questions: list[ForagingQuestion] = []

    def add_question(self, question: ForagingQuestion) -> None:
        """Register a potential question."""
        self._questions.append(question)

    def highest_impact(self, n: int = 3) -> list[ForagingQuestion]:
        """Return the N highest-impact unanswered questions."""
        return sorted(
            self._questions,
            key=lambda q: q.expected_impact,
            reverse=True,
        )[:n]

    def needs_more_evidence(self) -> bool:
        """True if any question exceeds the impact threshold."""
        return any(q.expected_impact >= self.impact_threshold for q in self._questions)
