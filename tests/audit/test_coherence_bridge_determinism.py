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


# --------------------------------------------------------------------------
# W6: subprocess must be gated behind an explicit DEV_ONLY flag.
# --------------------------------------------------------------------------


def test_subprocess_git_sha_returns_unknown_without_devonly_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audited paths MUST NOT shell out to git. Without the explicit
    ``NEOSYNAPTEX_ALLOW_SUBPROCESS_GIT=1`` flag, the helper returns a
    sentinel instead of invoking subprocess.
    """
    import core.coherence_bridge as module

    monkeypatch.delenv(module.ALLOW_SUBPROCESS_GIT_ENV, raising=False)

    def _fail(*_a: object, **_kw: object) -> None:
        raise AssertionError("subprocess.run must not be called without DEV_ONLY flag")

    monkeypatch.setattr(module.subprocess, "run", _fail)
    sha = module._subprocess_git_sha()
    assert sha == "unknown"


def test_runtime_context_default_prefers_env_var_over_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``RuntimeContext.default()`` must pick the canonical env var
    (``NEOSYNAPTEX_BUILD_GIT_SHA``) over any subprocess path."""
    import core.coherence_bridge as module

    monkeypatch.setenv(module.BUILD_SHA_ENV, "env_provided_sha")

    def _fail(*_a: object, **_kw: object) -> None:
        raise AssertionError("subprocess.run must not be called when env var is set")

    monkeypatch.setattr(module.subprocess, "run", _fail)
    ctx = RuntimeContext.default()
    assert ctx.build_git_sha == "env_provided_sha"


def test_runtime_context_default_skips_subprocess_without_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without ``NEOSYNAPTEX_ALLOW_SUBPROCESS_GIT=1`` or the build-SHA
    env var, ``default()`` resolves to the sentinel without ever
    touching subprocess."""
    import core.coherence_bridge as module

    monkeypatch.delenv(module.BUILD_SHA_ENV, raising=False)
    monkeypatch.delenv(module.ALLOW_SUBPROCESS_GIT_ENV, raising=False)

    def _fail(*_a: object, **_kw: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(module.subprocess, "run", _fail)
    ctx = RuntimeContext.default()
    assert ctx.build_git_sha == "unknown"


def test_export_bundle_is_subprocess_free_under_all_default_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: construct a bridge WITHOUT an explicit RuntimeContext
    (worst case: caller forgot to inject) and verify that export_bundle
    still never touches subprocess. This is the audited-export guarantee
    against an accidental default."""
    import core.coherence_bridge as module

    monkeypatch.delenv(module.BUILD_SHA_ENV, raising=False)
    monkeypatch.delenv(module.ALLOW_SUBPROCESS_GIT_ENV, raising=False)

    def _fail(*_a: object, **_kw: object) -> None:
        raise AssertionError("subprocess.run reached during default-construct export")

    monkeypatch.setattr(module.subprocess, "run", _fail)
    # No runtime= kwarg; exercises RuntimeContext.default().
    bridge = module.CoherenceBridge(engine=_StubEngine())
    blob = bridge.export_bundle()
    assert b"unknown" in blob  # sentinel SHA, not a real git hash


def test_devonly_flag_unlocks_subprocess_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the opt-in flag set, ``_subprocess_git_sha`` behaves as a
    thin shell-out. Kept as a regression test so the gate cannot rot
    into a hard removal without deliberate review."""
    import core.coherence_bridge as module

    monkeypatch.setenv(module.ALLOW_SUBPROCESS_GIT_ENV, "1")
    calls: list[list[str]] = []

    class _Result:
        stdout = "cafef00d\n"

    def _capture(cmd: list[str], **_kw: object) -> _Result:
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(module.subprocess, "run", _capture)
    sha = module._subprocess_git_sha()
    assert sha == "cafef00d"
    assert calls, "DEV_ONLY flag must unlock the subprocess path"
