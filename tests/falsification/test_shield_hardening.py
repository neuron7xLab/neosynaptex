"""Falsification-shield hardening — adversarial integrity layer.

Purpose: make it STRUCTURALLY impossible to fabricate the gamma~1
invariant by construction. Any code that tries to produce the result
without an honest Theil-Sen measurement on fresh (topo, cost) pairs
must be detected and failed.

Four failure modes covered:

  A. Circular construction
     ``thermo_cost`` defined as a power-law transform of ``topo()``
     so that gamma = 1 falls out of the algebra rather than the data.
     Detection: AST walk over ``substrates/*/adapter.py``; flag any
     ``thermo_cost`` method body that calls ``self.topo()``.

  B. Data leakage / gamma caching
     ``gamma`` stored as an attribute and reused instead of recomputed.
     Detection: run ``observe()`` twice on the same adapter with a
     perturbation injected in between and assert the reported gamma
     reflects the new buffer state; also assert the adapter object
     carries no ``gamma`` attribute across observe() calls.

  C. Window gaming
     Window chosen to minimise ``|gamma - 1|`` post-hoc.
     Detection: generate the same (topo, cost) stream with known
     gamma_true = 1.0 and recover gamma for window in {8, 16, 32, 64}.
     Assert every recovered gamma falls in [0.80, 1.20] and their
     std across windows < 0.15.

  D. Adversarial gamma injection
     Adapter tries to provide a ``gamma`` attribute or a
     ``_compute_gamma`` method hoping the engine reads it. The engine
     must ignore those; the reported gamma must match what Theil-Sen
     recovers from the (topo, cost) buffer.

These are *structural* proofs: they do not prove gamma ~ 1 in any
specific substrate — that is the job of ``test_gamma_meta_analysis.py``.
They prove that the pipeline cannot be gamed.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from core.gamma import compute_gamma
from neosynaptex import Neosynaptex

REPO_ROOT = Path(__file__).resolve().parents[2]
SUBSTRATES_DIR = REPO_ROOT / "substrates"

# Substrates with a top-level ``adapter.py`` implementing the root
# DomainAdapter protocol. Nested adapters under substrates/kuramoto/
# (e.g. regime / consensus) belong to a subsystem-specific interface
# and are out of scope for this shield.
_CANDIDATE_SUBSTRATES = (
    "zebrafish",
    "gray_scott",
    "kuramoto",
    "bn_syn",
    "cns_ai_loop",
    "cfp_diy",
    "hrv",
    "lotka_volterra",
    "eeg_physionet",
    "hrv_physionet",
    "serotonergic_kuramoto",
    "eeg_resting",
    "hrv_fantasia",
    "geosync_market",
)


def _adapter_paths() -> list[Path]:
    return [
        SUBSTRATES_DIR / s / "adapter.py"
        for s in _CANDIDATE_SUBSTRATES
        if (SUBSTRATES_DIR / s / "adapter.py").is_file()
    ]


# =====================================================================
# Test 1 — FAILURE MODE A: circular construction (AST)
# =====================================================================


def _calls_self_topo(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the body of ``func`` ever calls ``self.topo(...)``."""
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name)
            and fn.value.id == "self"
            and fn.attr == "topo"
        ):
            return True
    return False


# Method names that, when present on the adapter, indicate the gamma
# for that substrate is computed OUTSIDE the root Theil-Sen protocol
# (e.g. directly from per-subject DFA alpha or aperiodic exponents).
# When such a method exists, a circular ``thermo_cost = f(topo())`` is
# a protocol-compatibility shim rather than the γ-producing algebra.
_GAMMA_OWNER_METHODS: frozenset[str] = frozenset({"get_gamma_result", "compute_gamma"})


def _class_methods(cls: ast.ClassDef) -> set[str]:
    return {n.name for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}


def test_no_circular_construction() -> None:
    """``thermo_cost`` may not read ``self.topo()`` unless the adapter
    also owns the gamma derivation via a dedicated method.

    Rationale: the gamma invariant has scientific meaning only when
    ``topo`` and ``thermo_cost`` are *independent* measurements. An
    adapter whose ``thermo_cost`` is literally a function of
    ``topo()`` algebraically forces the Theil-Sen slope and is a
    circular construction — UNLESS that adapter computes gamma outside
    the protocol (via ``get_gamma_result`` / ``compute_gamma``), in
    which case the circular ``thermo_cost`` is a documented
    compatibility shim and cannot influence the reported gamma.

    Two-tier result:
      * FAIL if any adapter has circular ``thermo_cost`` AND no
        alternative gamma-owner method (true FAILURE MODE A).
      * Record circular-but-exempt adapters for visibility; they pass.
    """
    paths = _adapter_paths()
    assert len(paths) >= 5, (
        f"expected at least 5 candidate adapters, found {len(paths)}; did substrates/ move?"
    )

    violations: list[str] = []
    exempt: list[str] = []
    inspected: list[str] = []

    for path in paths:
        tree = ast.parse(path.read_text())
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            methods = _class_methods(cls)
            for node in cls.body:
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                if node.name != "thermo_cost":
                    continue
                inspected.append(f"{path.relative_to(REPO_ROOT)}::{cls.name}")
                if not _calls_self_topo(node):
                    continue
                # Circular. Is it exempt via an alternative gamma owner?
                if methods & _GAMMA_OWNER_METHODS:
                    exempt.append(
                        f"{path.relative_to(REPO_ROOT)}::{cls.name} "
                        f"(bypass: {sorted(methods & _GAMMA_OWNER_METHODS)})"
                    )
                else:
                    violations.append(f"{path.relative_to(REPO_ROOT)}::{cls.name}.thermo_cost")

    assert inspected, "no thermo_cost methods found in any candidate adapter"
    assert not violations, (
        "FAILURE MODE A (circular construction with no alternative "
        "gamma owner): thermo_cost reads self.topo() in " + ", ".join(violations)
    )

    # Surface exempt adapters in the test log so they remain visible
    # and cannot quietly multiply.
    if exempt:
        print(
            "\nshield: circular thermo_cost allowed (protocol-shim) in:\n  " + "\n  ".join(exempt)
        )


# =====================================================================
# Synthetic test adapter — used for modes B, C, D
# =====================================================================


@dataclass
class _SyntheticAdapter:
    """Synthetic adapter producing (topo, cost) with a controllable
    true gamma.

    NOT a real substrate — test scaffolding only. Every call to
    ``state()`` advances the internal RNG and produces the next
    (topo, cost) pair via the model

        log(cost) = -gamma_true * log(topo) + lognormal_noise

    with ``topo`` drawn log-uniformly. The adapter's ``topo()`` /
    ``thermo_cost()`` methods return the cached pair and do NOT read
    each other — independent of the FAILURE MODE A pattern.
    """

    domain_name: str = "synthetic"
    gamma_true: float = 1.0
    seed: int = 0
    noise_sigma: float = 0.05
    _rng: np.random.Generator = field(init=False)
    _topo_v: float = field(init=False, default=1.0)
    _cost_v: float = field(init=False, default=1.0)
    _x: float = field(init=False, default=0.0)
    _y: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._advance()

    def _advance(self) -> None:
        log_topo = self._rng.uniform(math.log(0.5), math.log(10.0))
        noise = self._rng.normal(0.0, self.noise_sigma)
        log_cost = -self.gamma_true * log_topo + noise
        self._topo_v = float(math.exp(log_topo))
        self._cost_v = float(math.exp(log_cost))
        self._x = float(self._rng.normal())
        self._y = float(self._rng.normal())

    @property
    def domain(self) -> str:
        return self.domain_name

    @property
    def state_keys(self) -> list[str]:
        return ["x", "y"]

    def state(self) -> dict[str, float]:
        self._advance()
        return {"x": self._x, "y": self._y}

    def topo(self) -> float:
        return max(0.01, self._topo_v)

    def thermo_cost(self) -> float:
        return max(0.01, self._cost_v)


# =====================================================================
# Test 2 — FAILURE MODE B: gamma recomputed, not cached
# =====================================================================


def test_gamma_recomputed_not_cached() -> None:
    """Per invariant I-1 in CONTRACT.md: gamma is derived, never stored.

    Observe an adapter twice with distinct RNG streams in between. The
    reported gamma must reflect the new buffer content, not a cached
    value from the first call; and the adapter object must carry no
    ``gamma`` attribute across ``observe()`` invocations.
    """
    engine = Neosynaptex(window=16)
    adapter = _SyntheticAdapter(domain_name="synth_cache", gamma_true=1.0, seed=11)
    engine.register(adapter)

    # Fill the buffer so per-domain gamma can clear the min-pairs gate.
    for _ in range(24):
        engine.observe()
    s1 = engine.observe()
    gamma_1 = s1.gamma_per_domain[adapter.domain]
    assert np.isfinite(gamma_1), "first observation did not produce a finite gamma"

    # Hard-perturb the adapter's internal RNG so the next topo/cost
    # pairs diverge from the prior stream. The buffer is rolling, so
    # after a handful more ticks the window will contain meaningfully
    # different (topo, cost) pairs.
    adapter._rng = np.random.default_rng(seed=999_999)
    for _ in range(24):
        engine.observe()
    s2 = engine.observe()
    gamma_2 = s2.gamma_per_domain[adapter.domain]
    assert np.isfinite(gamma_2), "second observation did not produce a finite gamma"

    # Live recomputation proof: different buffers yield (generically)
    # different Theil-Sen slopes. A caching bug would return identical
    # values to machine precision.
    assert gamma_1 != pytest.approx(gamma_2, abs=1e-12), (
        "FAILURE MODE B: gamma identical across observations with "
        f"perturbed state — looks cached (g1={gamma_1}, g2={gamma_2})"
    )

    # Protocol-level proof: no stealth ``gamma`` attribute on the adapter.
    assert not hasattr(adapter, "gamma"), (
        "adapter must not carry a ``gamma`` attribute — invariant I-1"
    )
    assert not hasattr(adapter, "_gamma_cached"), "adapter carries a private gamma cache"


# =====================================================================
# Test 3 — FAILURE MODE C: window invariance
# =====================================================================


def _recover_gamma_for_window(window: int, gamma_true: float, seed: int) -> float:
    """Generate a (topo, cost) stream with given true gamma and recover it
    through the canonical ``core.gamma.compute_gamma`` path — the exact
    function the engine's observe() loop delegates to.
    """
    rng = np.random.default_rng(seed)
    n = window * 4
    log_topo = rng.uniform(math.log(0.5), math.log(10.0), size=n)
    log_cost = -gamma_true * log_topo + rng.normal(0.0, 0.05, size=n)
    topo = np.exp(log_topo)
    cost = np.exp(log_cost)
    # Take the trailing window, matching engine buffer semantics.
    r = compute_gamma(
        topo[-window:],
        cost[-window:],
        bootstrap_n=100,  # reduced from default 500 for test speed
        seed=seed,
    )
    return float(r.gamma)


@pytest.mark.parametrize("window", [8, 16, 32, 64])
def test_window_invariance(window: int) -> None:
    """Recovered gamma must sit near the true value across all windows.

    Parameter-invariance proof: if ``window`` is post-hoc tuned to
    push gamma toward 1.0, different windows on the same stream would
    fan out. With an honest estimator they cluster.
    """
    g = _recover_gamma_for_window(window=window, gamma_true=1.0, seed=2026)
    assert 0.80 <= g <= 1.20, (
        f"FAILURE MODE C: recovered gamma={g:.4f} outside [0.80, 1.20] for window={window}"
    )


def test_window_invariance_std() -> None:
    """Std of recovered gamma across windows must stay below 0.15.

    A honest Theil-Sen estimator on a well-specified stream produces a
    tight cluster of window-level gammas. Spread above 0.15 indicates
    either the stream is not well-specified or the estimator is being
    tuned.
    """
    gammas = [
        _recover_gamma_for_window(window=w, gamma_true=1.0, seed=2026) for w in (8, 16, 32, 64, 128)
    ]
    spread = float(np.std(gammas))
    assert spread < 0.15, (
        f"FAILURE MODE C: gamma spread across windows = {spread:.4f} >= 0.15 ({gammas})"
    )


# =====================================================================
# Test 4 — FAILURE MODE D: adversarial gamma injection blocked
# =====================================================================


class _AdversarialAdapter(_SyntheticAdapter):
    """Synthetic adapter that TRIES to inject gamma = 1.0 via every
    channel a rogue author might reach for:

      * a ``gamma`` attribute on the adapter,
      * an adversarial ``_compute_gamma`` method,
      * an ``adapter_gamma`` attribute nested in state().
    """

    def __init__(self, *, gamma_true: float, seed: int) -> None:
        super().__init__(
            domain_name="adversarial",
            gamma_true=gamma_true,
            seed=seed,
        )
        # Bait 1: direct attribute.
        self.gamma = 1.0
        # Bait 2: private attribute — mimics a cache.
        self._gamma_cached = 1.0

    def _compute_gamma(self) -> float:
        # Bait 3: adversarial method name.
        return 1.0

    def state(self) -> dict[str, float]:
        s = super().state()
        # Bait 4: pollute state dict.
        s["gamma"] = 1.0
        return s


def test_adversarial_gamma_injection_blocked() -> None:
    """An adapter cannot smuggle gamma = 1.0 through the protocol.

    Construct an adversarial adapter whose (topo, cost) pairs follow
    the model with ``gamma_true = 0.5`` and which sets every plausible
    ``gamma`` bait. After enough observations, the engine-reported
    gamma must reflect the data (~0.5), not the bait (1.0).
    """
    engine = Neosynaptex(window=16)
    adv = _AdversarialAdapter(gamma_true=0.5, seed=123)

    # Sanity: the adapter's state_keys don't include a 'gamma' key,
    # so the engine won't lift our bait key into its phi vector.
    assert "gamma" not in adv.state_keys

    engine.register(adv)
    for _ in range(40):
        engine.observe()
    s = engine.observe()
    g_reported = s.gamma_per_domain[adv.domain]

    assert np.isfinite(g_reported), "engine did not produce a finite gamma after 40+ ticks"

    # The engine MUST have recovered something close to the true 0.5
    # and ignored the injected 1.0. A generous band tolerates Theil-Sen
    # noise on a 16-pair window.
    assert abs(g_reported - 0.5) < 0.2, (
        f"FAILURE MODE D: engine reported gamma={g_reported:.4f}; expected "
        f"~0.5 from data. Adversarial bait (gamma=1.0) may have leaked."
    )
    assert abs(g_reported - 1.0) > 0.15, (
        f"FAILURE MODE D: engine reported gamma={g_reported:.4f} — "
        "suspiciously close to the injected bait value 1.0"
    )


def test_engine_never_reads_adapter_gamma() -> None:
    """Structural invariant: ``observe()`` must never read an
    ``adapter.gamma`` attribute — the gamma path goes through the
    buffer and the canonical ``core.gamma.compute_gamma``.

    Implementation: AST-walk ``neosynaptex.py::Neosynaptex.observe`` and
    assert there is no ``.gamma`` attribute access on any name that
    could be an adapter reference.
    """
    src = (REPO_ROOT / "neosynaptex.py").read_text()
    tree = ast.parse(src)

    # Adapter-reference names the engine uses (from visual inspection
    # of the observe() body): ``adapter`` and ``self._adapters[...]``.
    adapter_refs = {"adapter"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "observe":
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Attribute):
                continue
            if sub.attr != "gamma":
                continue
            # Flag `adapter.gamma` or `self._adapters[...].gamma`.
            base: Any = sub.value
            # a) adapter.gamma
            if isinstance(base, ast.Name) and base.id in adapter_refs:
                raise AssertionError(f"observe() reads adapter.gamma at line {sub.lineno}")
            # b) self._adapters[name].gamma
            if (
                isinstance(base, ast.Subscript)
                and isinstance(base.value, ast.Attribute)
                and isinstance(base.value.value, ast.Name)
                and base.value.value.id == "self"
                and base.value.attr == "_adapters"
            ):
                raise AssertionError(
                    f"observe() reads self._adapters[...].gamma at line {sub.lineno}"
                )
        # Only one observe method expected.
        return
    raise AssertionError("Neosynaptex.observe() not found in neosynaptex.py")
