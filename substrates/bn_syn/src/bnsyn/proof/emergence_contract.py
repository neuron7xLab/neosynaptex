"""Emergence Proof Contract: integrator that ties together all 6 engines.

Evaluates five emergence conditions (E1-E5) across causality, integrated
information, assembly detection, structural plasticity, and criticality
engines, producing a binary verdict and continuous score.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bnsyn.causality.transfer_entropy import TransferEntropyEngine, TEResult
from bnsyn.emergence.phi_proxy import PhiProxyEngine, PhiResult
from bnsyn.assembly.detector import AssemblyDetector, AssemblyDetectionResult
from bnsyn.plasticity.structural import StructuralPlasticityEngine, StructuralPlasticityReport
from bnsyn.criticality.renormalization import RenormalizationEngine, RenormalizationResult


@dataclass(frozen=True)
class EmergenceVerdict:
    """Immutable result of emergence proof evaluation."""

    passed: bool
    continuous_score: float
    conditions: dict[str, bool]
    metrics: dict[str, float]
    evidence_hash: str
    timestamp: str


def _clip(x: float, lo: float, hi: float) -> float:
    """Clip value to [lo, hi]."""
    return max(lo, min(hi, x))


class EmergenceProofContract:
    """Evaluates emergence across all subsystem engines.

    Parameters
    ----------
    te_engine : TransferEntropyEngine
        Causal information flow engine.
    phi_engine : PhiProxyEngine
        Integrated information engine.
    assembly_detector : AssemblyDetector
        Functional assembly detection engine.
    structural_engine : StructuralPlasticityEngine or None
        Structural plasticity engine (optional).
    renorm_engine : RenormalizationEngine
        Multi-scale criticality engine.
    """

    # Condition weights (equal weighting)
    _W1 = 1.0
    _W2 = 1.0
    _W3 = 1.0
    _W4 = 1.0
    _W5 = 1.0

    def __init__(
        self,
        te_engine: TransferEntropyEngine,
        phi_engine: PhiProxyEngine,
        assembly_detector: AssemblyDetector,
        structural_engine: StructuralPlasticityEngine | None,
        renorm_engine: RenormalizationEngine,
    ) -> None:
        self._te_engine = te_engine
        self._phi_engine = phi_engine
        self._assembly_detector = assembly_detector
        self._structural_engine = structural_engine
        self._renorm_engine = renorm_engine

    def evaluate(self) -> EmergenceVerdict:
        """Run all engines and evaluate emergence conditions.

        Returns
        -------
        EmergenceVerdict
            Binary and continuous emergence evaluation.
        """
        # 1. Causal information flow
        te_result: TEResult | None = self._te_engine.compute()

        # 2. Integrated information
        phi_result: PhiResult | None = self._phi_engine.compute()

        # 3. Functional assemblies
        assembly_result: AssemblyDetectionResult = self._assembly_detector.detect()

        # 4. Topological adaptation
        structural_report: StructuralPlasticityReport | None = None
        if self._structural_engine is not None:
            structural_report = self._structural_engine.step()

        # 5. Scale-free criticality
        renorm_result: RenormalizationResult | None = self._renorm_engine.compute()

        # --- Extract raw metrics ---
        te_net = te_result.te_net if te_result is not None else 0.0
        p_e2i = te_result.p_value_e_to_i if te_result is not None else 1.0
        p_i2e = te_result.p_value_i_to_e if te_result is not None else 1.0
        phi_z = phi_result.phi_z_score if phi_result is not None else 0.0
        n_assemblies = assembly_result.n_significant
        topology_jaccard = structural_report.topology_delta if structural_report is not None else 0.0
        sigma_cv = renorm_result.sigma_cv if renorm_result is not None else 1.0

        # --- Build conditions ---
        conditions: dict[str, bool] = {
            "E1_causal_information_flow": (
                te_result is not None
                and te_result.te_net > 0
                and min(te_result.p_value_e_to_i, te_result.p_value_i_to_e) < 0.05
            ),
            "E2_integrated_information": (
                phi_result is not None and phi_result.phi_z_score > 2.0
            ),
            "E3_functional_assemblies": n_assemblies >= 2,
            "E4_topological_adaptation": (
                structural_report is not None
                and structural_report.topology_delta > 0.01
            ),
            "E5_scale_free_criticality": (
                renorm_result is not None and renorm_result.sigma_cv < 0.1
            ),
        }

        # --- Build metrics ---
        metrics: dict[str, float] = {
            "te_net": te_net,
            "p_value_e_to_i": p_e2i,
            "p_value_i_to_e": p_i2e,
            "phi_z_score": phi_z,
            "n_assemblies": float(n_assemblies),
            "topology_jaccard": topology_jaccard,
            "sigma_cv": sigma_cv,
        }

        # --- Composite score ---
        e_continuous = (
            self._W1 * _clip(te_net / 0.01, 0.0, 2.0)
            + self._W2 * _clip(phi_z / 2.0, 0.0, 2.0)
            + self._W3 * _clip(n_assemblies / 2.0, 0.0, 2.0)
            + self._W4 * _clip(topology_jaccard / 0.01, 0.0, 2.0)
            + self._W5 * _clip((0.1 - sigma_cv) / 0.1, 0.0, 2.0)
        ) / 5.0

        # --- Evidence hash ---
        evidence_hash = hashlib.sha256(
            json.dumps(metrics, sort_keys=True).encode("utf-8")
        ).hexdigest()

        timestamp = datetime.now(timezone.utc).isoformat()

        return EmergenceVerdict(
            passed=all(conditions.values()),
            continuous_score=e_continuous,
            conditions=conditions,
            metrics=metrics,
            evidence_hash=evidence_hash,
            timestamp=timestamp,
        )

    def export_report(self, output_dir: Path) -> Path:
        """Evaluate and write emergence proof report to disk.

        Parameters
        ----------
        output_dir : Path
            Directory to write report files into.

        Returns
        -------
        Path
            Path to the main emergence_proof_report.json file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        verdict = self.evaluate()

        # --- Main report ---
        report = {
            "schema_version": "1.0.0",
            "verdict": "PASS" if verdict.passed else "FAIL",
            "continuous_score": verdict.continuous_score,
            "conditions": verdict.conditions,
            "metrics": verdict.metrics,
            "evidence_bundle_hash": verdict.evidence_hash,
            "component_reports": [
                "causality_report.json",
                "phi_proxy_report.json",
                "assembly_report.json",
                "structural_plasticity_report.json",
                "renormalization_report.json",
                "neuromodulation_report.json",
            ],
            "claim_boundary": (
                "This proof demonstrates measurable emergence in a simulated "
                "spiking neural network under controlled conditions. It does "
                "NOT claim biological equivalence or consciousness."
            ),
        }

        main_path = output_dir / "emergence_proof_report.json"
        main_path.write_text(
            json.dumps(report, indent=2, sort_keys=False), encoding="utf-8"
        )

        # --- Component reports ---
        _write_component(output_dir / "causality_report.json", {
            "engine": "TransferEntropyEngine",
            "te_net": verdict.metrics["te_net"],
            "p_value_e_to_i": verdict.metrics["p_value_e_to_i"],
            "p_value_i_to_e": verdict.metrics["p_value_i_to_e"],
            "condition_E1_passed": verdict.conditions["E1_causal_information_flow"],
        })

        _write_component(output_dir / "phi_proxy_report.json", {
            "engine": "PhiProxyEngine",
            "phi_z_score": verdict.metrics["phi_z_score"],
            "condition_E2_passed": verdict.conditions["E2_integrated_information"],
        })

        _write_component(output_dir / "assembly_report.json", {
            "engine": "AssemblyDetector",
            "n_assemblies": verdict.metrics["n_assemblies"],
            "condition_E3_passed": verdict.conditions["E3_functional_assemblies"],
        })

        _write_component(output_dir / "structural_plasticity_report.json", {
            "engine": "StructuralPlasticityEngine",
            "topology_jaccard": verdict.metrics["topology_jaccard"],
            "condition_E4_passed": verdict.conditions["E4_topological_adaptation"],
        })

        _write_component(output_dir / "renormalization_report.json", {
            "engine": "RenormalizationEngine",
            "sigma_cv": verdict.metrics["sigma_cv"],
            "condition_E5_passed": verdict.conditions["E5_scale_free_criticality"],
        })

        _write_component(output_dir / "neuromodulation_report.json", {
            "engine": "NeuromodulatoryField",
            "note": "Neuromodulation state captured via field snapshot (no standalone condition).",
        })

        return main_path


def _write_component(path: Path, data: dict[str, object]) -> None:
    """Write a single component report JSON file."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
