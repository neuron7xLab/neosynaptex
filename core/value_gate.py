"""Unified value gate for deterministic action selection."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ValueGateConfig", "ValueGateInput", "ValueGateDecision", "evaluate_value_gate"]


@dataclass(frozen=True)
class ValueGateConfig:
    lambda_risk: float = 1.0
    lambda_uncertainty: float = 1.0
    lambda_drift: float = 1.0
    min_value_score: float = 0.0


@dataclass(frozen=True)
class ValueGateInput:
    utility: float
    risk: float
    uncertainty: float
    kl_drift: float
    counterfactual_score: float


@dataclass(frozen=True)
class ValueGateDecision:
    accepted: bool
    score: float
    reason: str


def evaluate_value_gate(inp: ValueGateInput, cfg: ValueGateConfig) -> ValueGateDecision:
    for name, value in {
        "risk": inp.risk,
        "uncertainty": inp.uncertainty,
        "kl_drift": inp.kl_drift,
        "lambda_risk": cfg.lambda_risk,
        "lambda_uncertainty": cfg.lambda_uncertainty,
        "lambda_drift": cfg.lambda_drift,
    }.items():
        if value < 0.0:
            raise ValueError(f"{name} must be >= 0")

    score = (
        inp.utility
        - cfg.lambda_risk * inp.risk
        - cfg.lambda_uncertainty * inp.uncertainty
        - cfg.lambda_drift * inp.kl_drift
    )
    if score < cfg.min_value_score:
        return ValueGateDecision(False, score, "blocked:value_below_threshold")
    if score < inp.counterfactual_score:
        return ValueGateDecision(False, score, "blocked:counterfactual_better")
    return ValueGateDecision(True, score, "accepted")
