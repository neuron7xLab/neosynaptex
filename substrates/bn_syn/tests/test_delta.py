from aoc.audit import AuditEngine
from aoc.contracts import load_task_contract
from aoc.delta import DeltaEngine
from aoc.generator import DeterministicMarkdownGenerator
from aoc.state import AOCState


def _contract():
    return load_task_contract(
        {
            "task_id": "t1",
            "objective": "deterministic objective",
            "artifact_type": "markdown_document",
            "max_iterations": 3,
            "coherence_threshold": 0.8,
            "innovation_band": {"min_delta": 0.0, "max_delta": 0.9},
            "delta_weights": {"semantic": 0.4, "structural": 0.3, "functional": 0.3},
            "constraints": {
                "required_sections": ["Context", "Method"],
                "forbidden_terms": ["TODO"],
                "min_length": 10,
                "max_length": 3000,
            },
            "invariants": {"must_include_objective": True, "must_preserve_required_sections": False},
            "generator": {"kind": "deterministic_markdown", "deterministic_seed": 1},
            "auditor": {"verifier_kind": "required_checks_ground_truth"},
            "output": {"artifact_filename": "final_artifact.md"},
        }
    )


def test_delta_decomposition_correctness() -> None:
    contract = _contract()
    state = AOCState(0, "z", None, None, None, None, contract.innovation_band, "INIT")
    content = DeterministicMarkdownGenerator().generate(state, contract, 1).content
    audit = AuditEngine().run(content, contract)
    d = DeltaEngine().compute(contract, content, audit.checks)
    assert 0 <= d.semantic_delta <= 1
    assert 0 <= d.structural_delta <= 1
    assert 0 <= d.functional_delta <= 1
    assert d.total_delta == (
        d.semantic_delta * 0.4 + d.structural_delta * 0.3 + d.functional_delta * 0.3
    )
