"""Tests for hypothesis verification with v2 results."""

import json
from pathlib import Path

import pytest


def assert_condition_normalized_blocks(results_dir: Path) -> None:
    """Assert normalized aggregates exist in condition JSON files."""
    for condition_file in results_dir.glob("*.json"):
        if condition_file.stem == "manifest":
            continue
        payload = json.loads(condition_file.read_text(encoding="utf-8"))
        aggregates = payload["aggregates"]
        assert "normalized" in aggregates, f"Missing normalized block in {condition_file}"
        normalized = aggregates["normalized"]
        assert "w_total_reduction_pct" in normalized, (
            f"Missing w_total_reduction_pct in {condition_file}"
        )
        assert "w_cons_reduction_pct" in normalized, (
            f"Missing w_cons_reduction_pct in {condition_file}"
        )
        assert "stability_w_total_var_end_minmax" in normalized, (
            f"Missing stability_w_total_var_end_minmax in {condition_file}"
        )


@pytest.mark.validation
def test_verify_hypothesis_v2_bundled_results() -> None:
    """Test that bundled v2 results pass hypothesis verification."""
    from experiments.verify_hypothesis import verify_hypothesis_h1

    results_dir = Path("results/temp_ablation_v2")

    if not results_dir.exists():
        pytest.skip("Bundled v2 results not found (expected in CI)")

    supported, verification = verify_hypothesis_h1(results_dir)

    # H1 should be supported
    assert supported, "Bundled v2 results should support H1"
    assert_condition_normalized_blocks(results_dir)

    # Check consolidation gates pass
    assert verification["consolidation_gates_pass"], "Consolidation gates should pass"
    assert verification["cooling_consolidation_nontrivial"], (
        "Cooling should have non-trivial consolidation"
    )
    assert verification["fixed_high_consolidation_nontrivial"], (
        "Fixed_high should have non-trivial consolidation"
    )

    # Check stability improvement
    assert verification["w_total_pass"], "w_total reduction should be >= 10%"
    assert verification["w_total_reduction_pct"] >= 10.0


@pytest.mark.validation
def test_verify_hypothesis_v1_bundled_results() -> None:
    """Test that bundled v1 results still work (for backward compatibility)."""
    from experiments.verify_hypothesis import verify_hypothesis_h1

    results_dir = Path("results/temp_ablation_v1")

    if not results_dir.exists():
        pytest.skip("Bundled v1 results not found")

    # v1 uses old verification logic (no consolidation gates for v1 condition name)
    # It should still verify successfully
    supported, verification = verify_hypothesis_h1(results_dir)

    # The logic will detect cooling_geometric and not apply strict gates
    # Just check it runs without error
    assert "supported" in verification
    assert_condition_normalized_blocks(results_dir)
