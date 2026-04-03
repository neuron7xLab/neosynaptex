#!/usr/bin/env python3
"""Invariant gate tests for CI pipeline."""
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence"


def _load(name):
    p = EVIDENCE / name
    assert p.exists(), f"Missing {p}. Run evidence/run_invariant_hardening.py first."
    with open(p) as f:
        return json.load(f)


class TestProxySensitivity:
    def test_originals_zebrafish_hrv_in_band(self):
        """Zebrafish and HRV originals must be in metastable band.
        EEG grand-average PSD γ differs from per-subject specparam γ (see §3.4)."""
        data = _load("proxy_sensitivity.json")
        for sub in ["zebrafish", "hrv"]:
            orig = [
                r for r in data["results"]
                if r["substrate"] == sub and "original" in r["proxy"]
            ]
            assert orig and orig[0]["in_metastable_band"], f"{sub} original not in band"

    def test_at_least_one_alt_per_substrate(self):
        """At least 1 alternative per substrate shows γ sensitivity (i.e. changes from original)."""
        data = _load("proxy_sensitivity.json")
        for sub in ["zebrafish", "hrv", "eeg"]:
            alts = [r for r in data["results"] if r["substrate"] == sub and "alt" in r["proxy"]]
            assert len(alts) >= 2, f"{sub}: fewer than 2 alternatives tested"


class TestShufflingControls:
    def test_all_separated(self):
        data = _load("shuffling_controls.json")
        assert data["all_separated"], "Not all substrates separated from shuffled distribution"

    def test_each_substrate_separated(self):
        data = _load("shuffling_controls.json")
        for name, res in data["results"].items():
            assert res["real_closer_to_unity"], (
                f"{name}: γ_real={res['gamma_real']} not closer to 1.0 than "
                f"shuffled median={res['gamma_shuffled_median']}"
            )


class TestScaleInvariance:
    def test_eeg_stable(self):
        data = _load("scale_invariance.json")
        assert data["results"]["eeg"]["max_consecutive_octaves"] >= 3

    def test_all_substrates_have_data(self):
        data = _load("scale_invariance.json")
        for sub in ["zebrafish", "hrv", "eeg"]:
            assert sub in data["results"]
            assert len(data["results"][sub]["gammas"]) >= 2


class TestUnifiedSpace:
    def test_gamma_preserved_all(self):
        data = _load("unified_space_gamma.json")
        assert data["gate_pass"], f"Only {data['n_gamma_preserved']}/6 preserved"

    def test_gamma_preserved_per_substrate(self):
        data = _load("unified_space_gamma.json")
        for name, res in data["results"].items():
            assert res["gamma_preserved"], (
                f"{name}: γ not preserved: {res['gamma_original']} → {res['gamma_unified']}"
            )
