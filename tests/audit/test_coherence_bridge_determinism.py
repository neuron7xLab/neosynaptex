"""Determinism regression tests for ``CoherenceBridge.export_bundle``.

Prior implementation embedded ``time.time()`` and a subprocess
``git rev-parse`` call at export time, so two back-to-back exports of
the same engine state produced different bytes. The current
implementation requires callers to inject a ``RuntimeContext``; under a
fixed context, the bundle is byte-stable.
"""

from __future__ import annotations

from typing import Any

import pytest

from core.coherence_bridge import CoherenceBridge, RuntimeContext


class _StubState:
    """Minimal duck-typed NeosynaptexState for the bridge."""

    def __init__(self) -> None:
        self.t = 7
        self.gamma_per_domain = {"A": 1.0, "B": 0.95}
        self.gamma_ci_per_domain = {"A": (0.9, 1.1), "B": (0.85, 1.05)}
        self.gamma_mean = 0.975
        self.gamma_std = 0.025
        self.cross_coherence = 0.9
        self.phase = "METASTABLE"
        self.spectral_radius = 0.8
        self.sr_per_domain = {"A": 0.82, "B": 0.78}
        self.anomaly_score = {"A": 0.1, "B": 0.15}
        self.modulation = {"A": 0.001, "B": -0.001}


class _StubEngine:
    """Duck-typed engine: minimum surface needed by the bridge."""

    def __init__(self) -> None:
        self._state = _StubState()

    def history(self) -> list[_StubState]:
        return [self._state]

    def export_proof(self) -> dict[str, Any]:
        # Deliberately unordered keys to verify the JSON emitter sorts them.
        return {
            "verdict": "INCONCLUSIVE",
            "chain": {"tick": 7, "self_hash": "abcdef"},
            "per_domain": {
                "B": {"gamma": 0.95},
                "A": {"gamma": 1.0},
            },
        }


def _bridge(rt: RuntimeContext) -> CoherenceBridge:
    return CoherenceBridge(engine=_StubEngine(), runtime=rt)


def test_export_bundle_is_byte_stable_under_fixed_runtime_context() -> None:
    rt = RuntimeContext.fixed(git_sha="fixed0123", timestamp=1_700_000_000.0)
    a = _bridge(rt).export_bundle()
    b = _bridge(rt).export_bundle()
    assert a == b


def test_export_bundle_uses_injected_git_sha_not_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # If the implementation ever regressed and started shelling out to
    # git during export, this test would catch it -- the monkeypatched
    # subprocess would explode.
    def _no_subprocess(*_a: object, **_kw: object) -> None:
        raise AssertionError("export_bundle must not invoke subprocess at export time")

    import core.coherence_bridge as module

    monkeypatch.setattr(module.subprocess, "run", _no_subprocess)

    rt = RuntimeContext.fixed(git_sha="deterministic_sha", timestamp=42.0)
    blob = _bridge(rt).export_bundle()
    assert b"deterministic_sha" in blob


def test_export_bundle_uses_injected_clock_not_wallclock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.coherence_bridge as module

    def _explode() -> float:
        raise AssertionError("export_bundle must not call time.time at export")

    monkeypatch.setattr(module.time, "time", _explode)
    rt = RuntimeContext(build_git_sha="sha1", clock=lambda: 99.0)
    blob = _bridge(rt).export_bundle()
    assert b"99.0" in blob


def test_snapshot_emits_timestamp_and_injected_sha() -> None:
    rt = RuntimeContext.fixed(git_sha="snap_sha", timestamp=1234.5)
    snap = _bridge(rt).snapshot()
    assert snap["git_sha"] == "snap_sha"
    assert snap["timestamp"] == 1234.5


def test_export_bundle_embeds_deterministic_fields() -> None:
    rt = RuntimeContext.fixed(git_sha="abc", timestamp=10.0)
    blob = _bridge(rt).export_bundle()
    # Injected metadata embedded directly.
    assert b"abc" in blob
    assert b"evidentiary_timestamp" in blob
    # Proof payload is sorted: A before B alphabetically.
    assert blob.index(b'"A"') < blob.index(b'"B"')


def test_two_engines_same_state_same_context_produce_same_bytes() -> None:
    rt = RuntimeContext.fixed(git_sha="shared", timestamp=0.0)
    a = _bridge(rt).export_bundle()
    b = _bridge(rt).export_bundle()
    assert a == b
