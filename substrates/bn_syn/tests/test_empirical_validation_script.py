"""Tests for empirical validation benchmark summarizer."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.empirical_validation import load_results, summarize, write_report


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "scenario": "s1",
        "performance_wall_time_sec_mean": 0.1,
        "stability_nan_rate_mean": 0.0,
        "stability_divergence_rate_mean": 0.0,
        "reproducibility_bitwise_delta_mean": 0.0,
        "learning_convergence_error_mean": 0.2,
    }
    row.update(overrides)
    return row


def test_load_results_rejects_non_list_payload(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{"scenario": "single"}', encoding="utf-8")

    with pytest.raises(ValueError, match="must be a list"):
        load_results(source)


def test_load_results_rejects_non_object_rows(tmp_path: Path) -> None:
    source = tmp_path / "invalid_rows.json"
    source.write_text('["bad"]', encoding="utf-8")

    with pytest.raises(ValueError, match="row at index 0 must be an object"):
        load_results(source)


def test_summarize_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="no benchmark scenarios found"):
        summarize([])


def test_summarize_rejects_missing_required_field() -> None:
    with pytest.raises(ValueError, match="missing required field 'scenario'"):
        summarize([{"performance_wall_time_sec_mean": 0.1}])


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("performance_wall_time_sec_mean", -1.0, r"must be >= 0"),
        ("stability_nan_rate_mean", float("nan"), "must be finite"),
        ("stability_divergence_rate_mean", float("inf"), "must be finite"),
        ("reproducibility_bitwise_delta_mean", True, "must be numeric"),
    ],
)
def test_summarize_rejects_invalid_numeric_values(field: str, value: object, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        summarize([_base_row(**{field: value})])


def test_summarize_stable_surface_has_no_pruned_branches() -> None:
    results = [
        _base_row(scenario="s1", performance_wall_time_sec_mean=0.1, learning_convergence_error_mean=0.2),
        _base_row(scenario="s2", performance_wall_time_sec_mean=0.2, learning_convergence_error_mean=0.4),
    ]

    summary, unstable = summarize(results)

    assert summary.median_wall_time_sec == pytest.approx(0.15)
    assert summary.stability_integrity_index == 1.0
    assert 0.0 <= summary.review_load_index <= 1.0
    assert summary.unstable_branch_count == 0
    assert unstable == []


def test_summarize_single_row_input_is_supported() -> None:
    summary, unstable = summarize([_base_row(performance_wall_time_sec_mean=0.25)])

    assert summary.scenario_count == 1
    assert summary.median_wall_time_sec == pytest.approx(0.25)
    assert summary.unstable_branch_count == 0
    assert unstable == []


def test_summarize_marks_unstable_branches_for_pruning() -> None:
    results = [
        _base_row(scenario="stable", performance_wall_time_sec_mean=0.1),
        _base_row(
            scenario="unstable",
            performance_wall_time_sec_mean=0.3,
            stability_divergence_rate_mean=0.2,
        ),
    ]

    summary, unstable = summarize(results)

    assert summary.unstable_branch_count == 1
    assert unstable[0]["scenario"] == "unstable"
    assert unstable[0]["action"] == "prune_from_default_stress_path"


def test_write_report_is_deterministic(tmp_path: Path) -> None:
    results = [_base_row()]
    summary, unstable = summarize(results)

    output_json = tmp_path / "objective_metrics.json"
    output_md = tmp_path / "report.md"

    write_report(summary, unstable, output_json, output_md)
    first_json = output_json.read_text(encoding="utf-8")
    first_md = output_md.read_text(encoding="utf-8")

    write_report(summary, unstable, output_json, output_md)
    second_json = output_json.read_text(encoding="utf-8")
    second_md = output_md.read_text(encoding="utf-8")

    assert first_json == second_json
    assert first_md == second_md
    assert first_json.endswith("\n")
