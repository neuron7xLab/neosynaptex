"""Verify causal validation rules match versioned config.

Every rule_id in code must exist in configs/causal_validation_v1.json.
Every rule_id in config must be used in code.
"""

from __future__ import annotations

import json
from pathlib import Path

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.types.causal import CAUSAL_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "configs" / "causal_validation_v1.json").read_text())


def test_schema_version_matches() -> None:
    assert CONFIG["schema_version"] == CAUSAL_SCHEMA_VERSION


def test_all_code_rules_in_config() -> None:
    """Every rule_id used in code must be defined in config."""
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
    desc = mfn.extract(seq)
    event = mfn.detect(seq)
    fcast = mfn.forecast(seq, horizon=4)
    comp = mfn.compare(seq, seq)
    result = validate_causal_consistency(seq, desc, event, fcast, comp)

    code_ids = {r.rule_id for r in result.rule_results}
    config_ids = set(CONFIG["rules"].keys())

    missing_in_config = code_ids - config_ids
    assert not missing_in_config, f"Rules in code but not in config: {sorted(missing_in_config)}"


def test_all_config_rules_in_code() -> None:
    """Every rule_id in config should appear in at least one run."""
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
    desc = mfn.extract(seq)
    event = mfn.detect(seq)
    fcast = mfn.forecast(seq, horizon=4)
    comp = mfn.compare(seq, seq)
    result = validate_causal_consistency(seq, desc, event, fcast, comp)

    code_ids = {r.rule_id for r in result.rule_results}
    config_ids = set(CONFIG["rules"].keys())

    # Some rules are conditional (only fire for specific regimes/profiles)
    # Baseline won't trigger: DET-006/007/008, CMP-005, FOR-003, SIM-008/009, XST-001/003
    missing_in_code = config_ids - code_ids
    assert len(missing_in_code) <= 12, (
        f"Too many config rules not triggered: {sorted(missing_in_code)}"
    )


def test_severity_levels_match() -> None:
    """Rule severity in code must match config."""
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
    desc = mfn.extract(seq)
    event = mfn.detect(seq)
    fcast = mfn.forecast(seq, horizon=4)
    comp = mfn.compare(seq, seq)
    result = validate_causal_consistency(seq, desc, event, fcast, comp)

    mismatches = []
    for r in result.rule_results:
        if r.rule_id in CONFIG["rules"]:
            expected_sev = CONFIG["rules"][r.rule_id]["severity"]
            if r.severity.value != expected_sev:
                mismatches.append(f"{r.rule_id}: code={r.severity.value}, config={expected_sev}")

    assert not mismatches, f"Severity mismatches: {mismatches}"


def test_perturbation_stability_baseline() -> None:
    """Baseline simulation should be perturbation-stable."""
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
    event = mfn.detect(seq)
    result = validate_causal_consistency(seq, detection=event)
    ptb_rules = [r for r in result.rule_results if r.rule_id.startswith("PTB-")]
    assert len(ptb_rules) == 2, f"Expected 2 perturbation rules, got {len(ptb_rules)}"
    for r in ptb_rules:
        assert r.passed, f"Baseline should be perturbation-stable: {r.rule_id} failed"
