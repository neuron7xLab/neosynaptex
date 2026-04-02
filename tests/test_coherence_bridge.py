"""10 tests for CoherenceBridge — external API surface."""

import json

import pytest

from core.coherence_bridge import CoherenceBridge, DomainDiagnostics, InterventionSuggestion
from neosynaptex import MockBnSynAdapter, MockMfnAdapter, MockPsycheCoreAdapter, Neosynaptex


def _make_engine(n_ticks: int = 40) -> Neosynaptex:
    engine = Neosynaptex(window=16)
    engine.register(MockBnSynAdapter())
    engine.register(MockMfnAdapter())
    engine.register(MockPsycheCoreAdapter())
    for _ in range(n_ticks):
        engine.observe()
    return engine


def test_snapshot_has_required_fields():
    bridge = CoherenceBridge(engine=_make_engine())
    snap = bridge.snapshot()
    assert "timestamp" in snap
    assert "gamma_global" in snap
    assert "phase" in snap
    assert "per_domain" in snap
    assert "git_sha" in snap


def test_snapshot_gamma_finite():
    bridge = CoherenceBridge(engine=_make_engine())
    snap = bridge.snapshot()
    assert snap["gamma_global"] is not None
    assert isinstance(snap["gamma_global"], float)


def test_snapshot_per_domain():
    bridge = CoherenceBridge(engine=_make_engine())
    snap = bridge.snapshot()
    assert len(snap["per_domain"]) >= 2
    for domain, diag in snap["per_domain"].items():
        assert "gamma" in diag
        assert "gamma_ci" in diag


def test_query_existing_domain():
    bridge = CoherenceBridge(engine=_make_engine())
    diag = bridge.query("spike")
    assert diag is not None
    assert isinstance(diag, DomainDiagnostics)
    assert diag.domain == "spike"


def test_query_missing_domain():
    bridge = CoherenceBridge(engine=_make_engine())
    diag = bridge.query("nonexistent")
    assert diag is None


def test_suggest_intervention_bounded():
    bridge = CoherenceBridge(engine=_make_engine())
    suggestion = bridge.suggest_intervention("spike")
    assert isinstance(suggestion, InterventionSuggestion)
    assert suggestion.magnitude <= 0.05
    assert suggestion.ssi_domain == "EXTERNAL"


def test_suggest_intervention_metastable():
    bridge = CoherenceBridge(engine=_make_engine())
    suggestion = bridge.suggest_intervention("morpho")
    assert suggestion.action in ("maintain", "observe", "dampen", "excite")


def test_export_bundle_json():
    bridge = CoherenceBridge(engine=_make_engine())
    data = bridge.export_bundle("json")
    assert isinstance(data, bytes)
    parsed = json.loads(data)
    assert "gamma" in parsed
    assert "chain" in parsed


def test_export_bundle_invalid_format():
    bridge = CoherenceBridge(engine=_make_engine())
    with pytest.raises(ValueError, match="Unsupported"):
        bridge.export_bundle("xml")


def test_snapshot_empty_engine():
    engine = Neosynaptex(window=16)
    engine.register(MockBnSynAdapter())
    bridge = CoherenceBridge(engine=engine)
    snap = bridge.snapshot()
    assert "error" in snap
