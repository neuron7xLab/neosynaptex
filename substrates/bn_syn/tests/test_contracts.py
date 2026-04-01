import pytest

from aoc.contracts import ContractError, InnovationBand, SigmaIndex, load_task_contract


def _payload() -> dict:
    return {
        "task_id": "t1",
        "objective": "objective text",
        "artifact_type": "markdown_document",
        "max_iterations": 3,
        "coherence_threshold": 0.8,
        "innovation_band": {"min_delta": 0.0, "max_delta": 0.8},
        "delta_weights": {"semantic": 0.4, "structural": 0.3, "functional": 0.3},
        "constraints": {
            "required_sections": ["Context", "Method"],
            "forbidden_terms": ["TODO"],
            "min_length": 10,
            "max_length": 1000,
        },
        "invariants": {
            "must_include_objective": True,
            "must_preserve_required_sections": False,
        },
        "generator": {"kind": "deterministic_markdown", "deterministic_seed": 7},
        "auditor": {"verifier_kind": "required_checks_ground_truth"},
        "output": {"artifact_filename": "final_artifact.md"},
    }


def test_contract_validation() -> None:
    contract = load_task_contract(_payload())
    assert contract.task_id == "t1"


def test_contract_invalid_weights() -> None:
    p = _payload()
    p["delta_weights"] = {"semantic": 0.7, "structural": 0.3, "functional": 0.3}
    with pytest.raises(ContractError):
        load_task_contract(p)


def test_sigma_secondary() -> None:
    sigma = SigmaIndex(0.1, 0.2, 0.3, 0.4)
    assert sigma.secondary_diagnostics == {"elasticity_raw": 0.3, "slope_raw": 0.4}


def test_innovation_band_bounds() -> None:
    with pytest.raises(ContractError):
        InnovationBand(0.6, 0.2)


def test_contract_missing_target_score_in_normalized_constraints_fails() -> None:
    p = _payload()
    p["normalized_constraints"] = {"other": 1.0}
    with pytest.raises(ContractError, match="normalized_constraints.target_score"):
        load_task_contract(p)


def test_contract_invalid_verifier_kind_fails() -> None:
    p = _payload()
    p["auditor"]["verifier_kind"] = "typoed_verifier"
    with pytest.raises(ContractError, match="auditor.verifier_kind"):
        load_task_contract(p)
