"""BN-Syn structural-evidence adapter.

This adapter is *not* a γ-producing substrate. It exposes BN-Syn's
local structural metrics (κ, avalanche distribution, phase coherence)
to NeoSynaptex as a separate, downgraded evidence channel. It refuses
to estimate γ from a single point — that requires multiple
(topo, cost) samples and is the job of the γ pipeline, not this
adapter.

Domain
------
``"spiking_emergent_dynamics"``

State keys
----------
``("kappa", "avalanche_fit_quality", "phase_coherence",
"phase_surrogate_rejected")``

Provenance
----------
``ProvenanceClass.DOWNGRADED`` + ``ClaimStatus.DOWNGRADED``. The
adapter is intentionally non-admissible in the REAL/CANONICAL/PROOF
pipeline; ``ensure_admissible`` will reject registration there. It is
admissible in DEMO/TEST modes for the structural-only path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.bnsyn_structural_evidence import (
    BnSynEvidenceVerdict,
    BnSynStructuralMetrics,
    validate_metrics,
)
from contracts.provenance import ClaimStatus, Provenance, ProvenanceClass

__all__ = [
    "BnSynStructuralAdapter",
    "AdapterStateView",
]


@dataclass(frozen=True, slots=True)
class AdapterStateView:
    """Read-only view of the adapter's externalised state."""

    kappa: float
    avalanche_fit_quality: float
    phase_coherence: float
    phase_surrogate_rejected: float  # bool stored as 0.0/1.0 to match adapter contract


class BnSynStructuralAdapter:
    """BN-Syn structural-evidence adapter.

    Wraps a ``BnSynStructuralMetrics`` snapshot and exposes the
    DomainAdapter-shaped surface NeoSynaptex's adapter registry uses.
    Importantly, this adapter does NOT participate in γ aggregation:
    the verdict computed via :meth:`compute_verdict` always reports
    ``gamma_status == NO_ADMISSIBLE_CLAIM`` unless the caller supplies
    a γ-side ``gamma_pass`` flag from a separate pipeline.
    """

    domain: str = "spiking_emergent_dynamics"
    state_keys: tuple[str, str, str, str] = (
        "kappa",
        "avalanche_fit_quality",
        "phase_coherence",
        "phase_surrogate_rejected",
    )

    #: Provenance — downgraded by construction. This adapter cannot
    #: enter REAL/CANONICAL/PROOF/REPLICATION modes.
    provenance: Provenance = Provenance(
        provenance_class=ProvenanceClass.DOWNGRADED,
        claim_status=ClaimStatus.DOWNGRADED,
        corpus_ref=(
            "BN-Syn canonical proof bundle "
            "(criticality + avalanche + phase_space + manifest + robustness)"
        ),
        notes=(
            "Local structural-evidence channel only. κ ≠ γ. "
            "Best honest verdict reachable from this adapter alone is "
            "LOCAL_STRUCTURAL_EVIDENCE_ONLY; VALIDATED_SUBSTRATE_EVIDENCE "
            "requires a γ-side pass from the caller's null-control pipeline."
        ),
    )

    def __init__(self, metrics: BnSynStructuralMetrics) -> None:
        if not isinstance(metrics, BnSynStructuralMetrics):
            raise TypeError(
                f"metrics must be BnSynStructuralMetrics, got {type(metrics).__name__}"
            )
        self._metrics = metrics
        self._validation_reasons = validate_metrics(metrics)

    # ------------------------------------------------------------------
    # DomainAdapter-shaped surface
    # ------------------------------------------------------------------
    def state(self) -> dict[str, float]:
        """Return the externalised structural state.

        Boolean ``phase_surrogate_rejected`` is stored as 0.0/1.0 to
        satisfy the registry's ``state[k]`` numeric-only contract.
        Non-finite or invalid metrics are clamped to NaN so the
        registry's runtime validator can flag them rather than letting
        a silent zero through.
        """
        m = self._metrics
        return {
            "kappa": float(m.kappa) if isinstance(m.kappa, (int, float)) else float("nan"),
            "avalanche_fit_quality": (
                float(m.avalanche_fit_quality)
                if isinstance(m.avalanche_fit_quality, (int, float))
                else float("nan")
            ),
            "phase_coherence": (
                float(m.phase_coherence)
                if isinstance(m.phase_coherence, (int, float))
                else float("nan")
            ),
            "phase_surrogate_rejected": (
                1.0 if m.phase_surrogate_rejected is True else 0.0
            ),
        }

    def topo(self) -> float:
        """Refuse to derive a topological observable from κ alone.

        This adapter is structural-only. Deriving ``topo`` from κ
        without an independent (topo, cost) population would amount
        to fabricating a γ source, which the integration protocol
        explicitly forbids. Raising NotImplementedError makes the
        adapter unusable for γ aggregation — by design.
        """
        raise NotImplementedError(
            "BnSynStructuralAdapter is structural-only; topo() is intentionally absent "
            "to prevent fabrication of a γ source from a single κ point."
        )

    def thermo_cost(self) -> float:
        """Refuse to derive a thermodynamic cost from κ alone.

        See :meth:`topo`. Same reasoning, same fail-closed behaviour.
        """
        raise NotImplementedError(
            "BnSynStructuralAdapter is structural-only; thermo_cost() is intentionally "
            "absent to prevent fabrication of a γ source from a single κ point."
        )

    # ------------------------------------------------------------------
    # Verdict surface
    # ------------------------------------------------------------------
    def compute_verdict(
        self,
        thresholds: dict[str, Any],
        *,
        provenance_ok: bool = True,
        determinism_ok: bool = True,
        gamma_pass: bool | None = None,
    ) -> BnSynEvidenceVerdict:
        """Compute the fail-closed verdict for the wrapped metrics.

        ``provenance_ok`` and ``determinism_ok`` are caller-supplied
        because the adapter, unlike the importer, does not have direct
        access to the bundle. The caller is the importer or a test
        harness that has already inspected the manifest.

        ``gamma_pass`` is the caller's γ-side judgement. ``None``
        (default) means "no γ-side pass available" → verdict cannot
        upgrade past LOCAL_STRUCTURAL_EVIDENCE_ONLY.
        """

        if self._validation_reasons:
            return BnSynEvidenceVerdict(
                local_structural_status="MISSING",
                gamma_status="NO_ADMISSIBLE_CLAIM",
                artifact_status="MISSING",
                claim_status="NO_ADMISSIBLE_CLAIM",
                reasons=self._validation_reasons,
            )

        m = self._metrics

        if not m.phase_surrogate_rejected:
            return BnSynEvidenceVerdict(
                local_structural_status="FAIL",
                gamma_status="NO_ADMISSIBLE_CLAIM",
                artifact_status="ARTIFACT_SUSPECTED",
                claim_status="ARTIFACT_SUSPECTED",
                reasons=("PHASE_SURROGATE_NOT_REJECTED",),
            )

        local_pass = self._local_pass(thresholds)
        local_status = "PASS" if local_pass else "FAIL"
        gamma_status = (
            "NO_ADMISSIBLE_CLAIM"
            if gamma_pass is None
            else ("PASS" if gamma_pass else "FAIL")
        )

        reasons: list[str] = []
        if not provenance_ok:
            reasons.append("PROVENANCE_MISSING")
        if not determinism_ok:
            reasons.append("DETERMINISM_NOT_REPLAYED")

        if not provenance_ok or not determinism_ok:
            if local_pass:
                return BnSynEvidenceVerdict(
                    local_structural_status=local_status,
                    gamma_status=gamma_status,
                    artifact_status="NOT_SUSPECTED",
                    claim_status="LOCAL_STRUCTURAL_EVIDENCE_ONLY",
                    reasons=tuple(reasons),
                )
            reasons.append("LOCAL_STRUCTURAL_FAIL")
            return BnSynEvidenceVerdict(
                local_structural_status=local_status,
                gamma_status=gamma_status,
                artifact_status="NOT_SUSPECTED",
                claim_status="NO_ADMISSIBLE_CLAIM",
                reasons=tuple(reasons),
            )

        if local_pass and gamma_pass is True:
            return BnSynEvidenceVerdict(
                local_structural_status=local_status,
                gamma_status=gamma_status,
                artifact_status="NOT_SUSPECTED",
                claim_status="VALIDATED_SUBSTRATE_EVIDENCE",
                reasons=(),
            )

        if local_pass:
            return BnSynEvidenceVerdict(
                local_structural_status=local_status,
                gamma_status=gamma_status,
                artifact_status="NOT_SUSPECTED",
                claim_status="LOCAL_STRUCTURAL_EVIDENCE_ONLY",
                reasons=tuple(reasons),
            )

        reasons.append("LOCAL_STRUCTURAL_FAIL")
        return BnSynEvidenceVerdict(
            local_structural_status=local_status,
            gamma_status=gamma_status,
            artifact_status="NOT_SUSPECTED",
            claim_status="NO_ADMISSIBLE_CLAIM",
            reasons=tuple(reasons),
        )

    def _local_pass(self, thresholds: dict[str, Any]) -> bool:
        import math

        m = self._metrics
        kappa_cfg = thresholds.get("kappa", {})
        target = float(kappa_cfg.get("target", 1.0))
        tolerance = float(kappa_cfg.get("tolerance", 0.1))

        kappa_ok_point = math.isfinite(m.kappa) and abs(m.kappa - target) <= tolerance
        kappa_ok_ci = (
            m.kappa_ci_low is not None
            and m.kappa_ci_high is not None
            and math.isfinite(m.kappa_ci_low)
            and math.isfinite(m.kappa_ci_high)
            and m.kappa_ci_low <= target <= m.kappa_ci_high
        )
        if not (kappa_ok_point or kappa_ok_ci):
            return False

        aval_cfg = thresholds.get("avalanche", {})
        fit_floor = float(aval_cfg.get("fit_quality_floor", 0.0))
        min_count = int(aval_cfg.get("min_avalanche_count", 0))

        if not isinstance(m.avalanche_distribution_summary, dict):
            return False
        if len(m.avalanche_distribution_summary) == 0:
            return False
        count = m.avalanche_distribution_summary.get("avalanche_count")
        if not isinstance(count, (int, float)) or isinstance(count, bool) or count < min_count:
            return False
        if not math.isfinite(m.avalanche_fit_quality):
            return False
        if m.avalanche_fit_quality < fit_floor:
            return False

        coh_cfg = thresholds.get("phase_coherence", {})
        coh_floor = float(coh_cfg.get("min_value", 0.0))
        if not math.isfinite(m.phase_coherence):
            return False
        if m.phase_coherence < coh_floor:
            return False
        return bool(m.phase_surrogate_rejected)
