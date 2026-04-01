from __future__ import annotations

from pathlib import Path


def _quickstart_smoke_commands() -> set[str]:
    makefile = Path("Makefile").read_text(encoding="utf-8").splitlines()
    in_target = False
    commands: set[str] = set()
    for line in makefile:
        if line.startswith("quickstart-smoke:"):
            in_target = True
            continue
        if in_target and line and not line.startswith("\t"):
            break
        if in_target and line.startswith("\t"):
            commands.add(line.strip())
    return commands


def test_readme_quickstart_contract_matches_make_target() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    expected = {
        "make quickstart-smoke",
        "bnsyn run --profile canonical --plot --export-proof",
        "artifacts/canonical_run/index.html",
        "artifacts/canonical_run/product_summary.json",
        "artifacts/canonical_run/proof_report.json",
        "artifacts/canonical_run/summary_metrics.json",
        "artifacts/canonical_run/criticality_report.json",
        "artifacts/canonical_run/avalanche_report.json",
        "artifacts/canonical_run/phase_space_report.json",
        "artifacts/canonical_run/emergence_plot.png",
        "docs/STATUS.md",
    }
    for command in expected:
        assert command in readme

    smoke_commands = _quickstart_smoke_commands()
    assert "$(PYTHON) -m scripts.check_quickstart_consistency" in smoke_commands
    assert "$(PYTHON) -m bnsyn --help" in smoke_commands
    assert "$(PYTHON) -m bnsyn run --help" in smoke_commands
    assert any(
        cmd.startswith(
            "$(PYTHON) -m bnsyn run --profile canonical --plot --export-proof --output artifacts/canonical_run | $(PYTHON) -c"
        )
        for cmd in smoke_commands
    )
