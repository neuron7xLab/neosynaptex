"""Contract tests for ``contracts/bnsyn_structural_evidence.py``.

Numbered tests:
1. ``BnSynStructuralMetrics`` is frozen and slotted.
2. ``BnSynEvidenceVerdict`` is frozen and slotted.
3. ``validate_metrics`` rejects NaN κ.
4. ``validate_metrics`` rejects ±inf κ.
5. ``validate_metrics`` accepts a fully-valid metric block.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.bnsyn_structural_evidence import (  # noqa: E402
    BnSynEvidenceVerdict,
    BnSynStructuralMetrics,
    validate_metrics,
)


def _good_metrics(**overrides: object) -> BnSynStructuralMetrics:
    base: dict[str, object] = {
        "kappa": 1.02,
        "kappa_ci_low": 0.95,
        "kappa_ci_high": 1.08,
        "avalanche_fit_quality": 0.42,
        "avalanche_distribution_summary": {
            "avalanche_count": 250,
            "size_max": 87,
            "alpha": 1.51,
        },
        "phase_coherence": 0.73,
        "phase_surrogate_rejected": True,
    }
    base.update(overrides)
    return BnSynStructuralMetrics(**base)  # type: ignore[arg-type]


# 1
def test_metrics_is_frozen_and_slotted() -> None:
    m = _good_metrics()
    with pytest.raises((AttributeError, TypeError, _frozen_instance_error_cls())):
        m.kappa = 0.0  # type: ignore[misc]


# 2
def test_verdict_is_frozen_and_slotted() -> None:
    v = BnSynEvidenceVerdict(
        local_structural_status="PASS",
        gamma_status="NO_ADMISSIBLE_CLAIM",
        artifact_status="NOT_SUSPECTED",
        claim_status="LOCAL_STRUCTURAL_EVIDENCE_ONLY",
        reasons=(),
    )
    with pytest.raises((AttributeError, TypeError, _frozen_instance_error_cls())):
        v.claim_status = "VALIDATED_SUBSTRATE_EVIDENCE"  # type: ignore[misc]


# 3
def test_validate_rejects_nan_kappa() -> None:
    m = _good_metrics(kappa=float("nan"))
    reasons = validate_metrics(m)
    assert "KAPPA_NOT_FINITE" in reasons


# 4
def test_validate_rejects_inf_kappa() -> None:
    for bad in (float("inf"), float("-inf")):
        m = _good_metrics(kappa=bad)
        assert "KAPPA_NOT_FINITE" in validate_metrics(m)


# 5
def test_validate_accepts_good_metrics() -> None:
    m = _good_metrics()
    assert validate_metrics(m) == ()
    assert math.isfinite(m.kappa)


# Helpers ---------------------------------------------------------------


def _frozen_instance_error_cls() -> type[BaseException]:
    """Look up FrozenInstanceError lazily to keep the import surface narrow."""
    import dataclasses

    return dataclasses.FrozenInstanceError
