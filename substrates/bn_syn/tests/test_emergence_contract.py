"""Tests for EmergenceProofContract — the integrator across all 6 engines."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from bnsyn.causality.transfer_entropy import TEResult
from bnsyn.emergence.phi_proxy import PhiResult
from bnsyn.assembly.detector import AssemblyDetectionResult, Assembly
from bnsyn.plasticity.structural import StructuralPlasticityReport
from bnsyn.criticality.renormalization import RenormalizationResult, ScaleMetrics
from bnsyn.proof.emergence_contract import EmergenceProofContract


# ---------------------------------------------------------------------------
# Mock engine factories
# ---------------------------------------------------------------------------

def _make_te_engine(*, te_net: float = 0.05, p_e2i: float = 0.01, p_i2e: float = 0.02):
    """Return a mock TransferEntropyEngine with controlled compute() output."""
    engine = MagicMock()
    engine.compute.return_value = TEResult(
        te_e_to_i=max(te_net, 0.0),
        te_i_to_e=0.0,
        te_net=te_net,
        p_value_e_to_i=p_e2i,
        p_value_i_to_e=p_i2e,
        timestamp_step=100,
    )
    return engine


def _make_phi_engine(*, phi_z: float = 3.5):
    """Return a mock PhiProxyEngine with controlled compute() output."""
    engine = MagicMock()
    engine.compute.return_value = PhiResult(
        phi_mean=0.5,
        phi_std=0.1,
        phi_max=0.8,
        phi_shuffled_mean=0.1,
        phi_z_score=phi_z,
        n_subsamples=5,
        best_partition=([0, 1], [2, 3]),
        timestamp_step=100,
    )
    return engine


def _make_assembly_detector(*, n_significant: int = 3):
    """Return a mock AssemblyDetector with controlled detect() output."""
    detector = MagicMock()
    assemblies = [
        Assembly(
            index=i,
            weights=np.zeros(10, dtype=np.float64),
            eigenvalue=2.0 + i,
            core_neurons=[i, i + 1],
        )
        for i in range(n_significant)
    ]
    detector.detect.return_value = AssemblyDetectionResult(
        assemblies=assemblies,
        n_significant=n_significant,
        marchenko_pastur_threshold=1.5,
        total_variance_explained=0.6,
        activation_traces={},
        timestamp_step=100,
    )
    return detector


def _make_structural_engine(*, topology_delta: float = 0.05):
    """Return a mock StructuralPlasticityEngine with controlled step() output."""
    engine = MagicMock()
    engine.step.return_value = StructuralPlasticityReport(
        synapses_pruned=5,
        synapses_sprouted=3,
        current_nnz_exc=500,
        current_nnz_inh=200,
        density_exc=0.1,
        density_inh=0.05,
        topology_delta=topology_delta,
    )
    return engine


def _make_renorm_engine(*, sigma_cv: float = 0.05):
    """Return a mock RenormalizationEngine with controlled compute() output."""
    engine = MagicMock()
    engine.compute.return_value = RenormalizationResult(
        scales=[
            ScaleMetrics(scale=0, n_groups=100, sigma=1.0, avalanche_exponent=1.5, entropy_rate=0.8),
            ScaleMetrics(scale=1, n_groups=25, sigma=0.98, avalanche_exponent=1.45, entropy_rate=0.78),
        ],
        sigma_cv=sigma_cv,
        tau_cv=0.02,
        entropy_cv=0.01,
        scale_invariant=sigma_cv < 0.1,
        flow_trajectory=[(1.0, 1.5, 0.8), (0.98, 1.45, 0.78)],
        timestamp_step=100,
    )
    return engine


def _build_contract(**overrides) -> EmergenceProofContract:
    """Build an EmergenceProofContract with all-passing defaults, applying overrides."""
    te = overrides.get("te_engine", _make_te_engine())
    phi = overrides.get("phi_engine", _make_phi_engine())
    asm = overrides.get("assembly_detector", _make_assembly_detector())
    struct = overrides.get("structural_engine", _make_structural_engine())
    renorm = overrides.get("renorm_engine", _make_renorm_engine())
    return EmergenceProofContract(te, phi, asm, struct, renorm)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAllConditionsPass:
    """When all engines return passing values, the verdict should pass."""

    def test_verdict_passed(self):
        contract = _build_contract()
        verdict = contract.evaluate()
        assert verdict.passed is True

    def test_all_conditions_true(self):
        contract = _build_contract()
        verdict = contract.evaluate()
        for name, val in verdict.conditions.items():
            assert val is True, f"Condition {name} should be True"

    def test_continuous_score_positive(self):
        contract = _build_contract()
        verdict = contract.evaluate()
        assert verdict.continuous_score > 0.0


class TestPartialFail:
    """When one engine returns None, the verdict should fail."""

    def test_te_none_fails(self):
        te = MagicMock()
        te.compute.return_value = None
        contract = _build_contract(te_engine=te)
        verdict = contract.evaluate()
        assert verdict.passed is False
        assert verdict.conditions["E1_causal_information_flow"] is False

    def test_phi_none_fails(self):
        phi = MagicMock()
        phi.compute.return_value = None
        contract = _build_contract(phi_engine=phi)
        verdict = contract.evaluate()
        assert verdict.passed is False
        assert verdict.conditions["E2_integrated_information"] is False

    def test_structural_none_fails(self):
        contract = _build_contract(structural_engine=None)
        verdict = contract.evaluate()
        assert verdict.passed is False
        assert verdict.conditions["E4_topological_adaptation"] is False

    def test_renorm_none_fails(self):
        renorm = MagicMock()
        renorm.compute.return_value = None
        contract = _build_contract(renorm_engine=renorm)
        verdict = contract.evaluate()
        assert verdict.passed is False
        assert verdict.conditions["E5_scale_free_criticality"] is False

    def test_continuous_score_below_max(self):
        te = MagicMock()
        te.compute.return_value = None
        contract = _build_contract(te_engine=te)
        verdict = contract.evaluate()
        assert verdict.continuous_score < 2.0


class TestContinuousScoreRange:
    """Continuous score should always be in [0, 2]."""

    def test_all_pass_in_range(self):
        verdict = _build_contract().evaluate()
        assert 0.0 <= verdict.continuous_score <= 2.0

    def test_all_none_in_range(self):
        te = MagicMock()
        te.compute.return_value = None
        phi = MagicMock()
        phi.compute.return_value = None
        renorm = MagicMock()
        renorm.compute.return_value = None
        asm = _make_assembly_detector(n_significant=0)
        contract = _build_contract(
            te_engine=te, phi_engine=phi,
            structural_engine=None, renorm_engine=renorm,
            assembly_detector=asm,
        )
        verdict = contract.evaluate()
        assert 0.0 <= verdict.continuous_score <= 2.0

    def test_extreme_values_in_range(self):
        # Very large passing values -- score should still cap at 2.0
        te = _make_te_engine(te_net=100.0, p_e2i=0.0, p_i2e=0.0)
        phi = _make_phi_engine(phi_z=1000.0)
        asm = _make_assembly_detector(n_significant=100)
        struct = _make_structural_engine(topology_delta=10.0)
        renorm = _make_renorm_engine(sigma_cv=0.0)
        contract = _build_contract(
            te_engine=te, phi_engine=phi,
            assembly_detector=asm, structural_engine=struct,
            renorm_engine=renorm,
        )
        verdict = contract.evaluate()
        assert 0.0 <= verdict.continuous_score <= 2.0


class TestExportCreatesFile:
    """export_report should write the main report to disk."""

    def test_file_exists(self, tmp_path: Path):
        contract = _build_contract()
        report_path = contract.export_report(tmp_path)
        assert report_path.exists()
        assert report_path.name == "emergence_proof_report.json"

    def test_component_reports_exist(self, tmp_path: Path):
        contract = _build_contract()
        contract.export_report(tmp_path)
        expected_files = [
            "causality_report.json",
            "phi_proxy_report.json",
            "assembly_report.json",
            "structural_plasticity_report.json",
            "renormalization_report.json",
            "neuromodulation_report.json",
        ]
        for fname in expected_files:
            assert (tmp_path / fname).exists(), f"{fname} not found"

    def test_report_valid_json(self, tmp_path: Path):
        contract = _build_contract()
        report_path = contract.export_report(tmp_path)
        data = json.loads(report_path.read_text())
        assert data["schema_version"] == "1.0.0"
        assert data["verdict"] in ("PASS", "FAIL")
        assert "claim_boundary" in data

    def test_creates_subdirectory(self, tmp_path: Path):
        nested = tmp_path / "sub" / "dir"
        contract = _build_contract()
        report_path = contract.export_report(nested)
        assert report_path.exists()


class TestEvidenceHashDeterministic:
    """Same inputs must produce the same evidence hash."""

    def test_same_hash(self):
        contract1 = _build_contract()
        contract2 = _build_contract()
        v1 = contract1.evaluate()
        v2 = contract2.evaluate()
        assert v1.evidence_hash == v2.evidence_hash

    def test_different_inputs_different_hash(self):
        contract1 = _build_contract()
        contract2 = _build_contract(te_engine=_make_te_engine(te_net=0.99))
        v1 = contract1.evaluate()
        v2 = contract2.evaluate()
        assert v1.evidence_hash != v2.evidence_hash
