"""CoherenceBridge — production-ready external API surface for NeoSynaptex.

JSON-RPC style, no HTTP dependencies. SSI external enforced.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 — used only for hardcoded git command
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import numpy as np

from core.contracts import SSIDomain, ssi_apply
from core.event_bus import EventBus, SubstrateEvent


@dataclass(frozen=True)
class DomainDiagnostics:
    domain: str
    gamma: float
    gamma_ci: tuple[float, float]
    spectral_radius: float
    anomaly_score: float
    modulation: float
    phase_contribution: str


@dataclass(frozen=True)
class InterventionSuggestion:
    domain: str
    action: str
    magnitude: float
    reason: str
    ssi_domain: str = "EXTERNAL"


class CoherenceBridge:
    """External interface to NeoSynaptex — read-only diagnostics + bounded suggestions.

    All modulation suggestions are SSI.EXTERNAL enforced.
    """

    def __init__(self, engine: Any, event_bus: EventBus | None = None) -> None:
        self._engine = engine
        self._bus = event_bus or EventBus()

    def snapshot(self) -> dict[str, Any]:
        """Current state of all substrates + global gamma + phase."""
        history = self._engine.history()
        if not history:
            return {"error": "no observations", "timestamp": time.time()}

        state = history[-1]
        git_sha = self._get_git_sha()

        per_domain = {}
        for domain, gamma in state.gamma_per_domain.items():
            ci = state.gamma_ci_per_domain.get(domain, (float("nan"), float("nan")))
            per_domain[domain] = {
                "gamma": float(gamma) if np.isfinite(gamma) else None,
                "gamma_ci": [
                    float(ci[0]) if np.isfinite(ci[0]) else None,
                    float(ci[1]) if np.isfinite(ci[1]) else None,
                ],
                "spectral_radius": float(state.sr_per_domain.get(domain, float("nan")))
                if np.isfinite(state.sr_per_domain.get(domain, float("nan")))
                else None,
                "anomaly_score": float(state.anomaly_score.get(domain, float("nan")))
                if np.isfinite(state.anomaly_score.get(domain, float("nan")))
                else None,
                "modulation": state.modulation.get(domain, 0.0),
            }

        return {
            "timestamp": time.time(),
            "git_sha": git_sha,
            "tick": state.t,
            "gamma_global": float(state.gamma_mean) if np.isfinite(state.gamma_mean) else None,
            "gamma_std": float(state.gamma_std) if np.isfinite(state.gamma_std) else None,
            "cross_coherence": float(state.cross_coherence)
            if np.isfinite(state.cross_coherence)
            else None,
            "phase": state.phase,
            "spectral_radius": float(state.spectral_radius)
            if np.isfinite(state.spectral_radius)
            else None,
            "per_domain": per_domain,
        }

    def subscribe(self, event_type: str) -> Generator[SubstrateEvent, None, None]:
        """Event stream generator. Yields events of given type."""
        queue: list[SubstrateEvent] = []
        self._bus.subscribe(event_type, lambda e: queue.append(e))
        while True:
            while queue:
                yield queue.pop(0)
            time.sleep(0.01)

    def query(self, domain: str) -> DomainDiagnostics | None:
        """Detailed diagnostics for a specific domain."""
        history = self._engine.history()
        if not history:
            return None

        state = history[-1]
        if domain not in state.gamma_per_domain:
            return None

        gamma = state.gamma_per_domain[domain]
        ci = state.gamma_ci_per_domain.get(domain, (float("nan"), float("nan")))
        sr = state.sr_per_domain.get(domain, float("nan"))
        anomaly = state.anomaly_score.get(domain, float("nan"))
        mod = state.modulation.get(domain, 0.0)

        return DomainDiagnostics(
            domain=domain,
            gamma=gamma,
            gamma_ci=ci,
            spectral_radius=sr,
            anomaly_score=anomaly,
            modulation=mod,
            phase_contribution=state.phase,
        )

    def suggest_intervention(self, domain: str) -> InterventionSuggestion:
        """Suggest bounded intervention. SSI.EXTERNAL enforced."""
        # Enforce SSI external — pass domain name as signal for validation
        ssi_apply(domain, SSIDomain.EXTERNAL)

        history = self._engine.history()
        if not history:
            return InterventionSuggestion(
                domain=domain,
                action="observe",
                magnitude=0.0,
                reason="no observations available",
            )

        state = history[-1]
        gamma = state.gamma_per_domain.get(domain, float("nan"))
        mod = state.modulation.get(domain, 0.0)

        if not np.isfinite(gamma):
            action = "observe"
            magnitude = 0.0
            reason = "gamma not yet computed"
        elif gamma > 1.15:
            action = "dampen"
            magnitude = min(abs(mod), 0.05)
            reason = f"gamma={gamma:.3f} above metastable band"
        elif gamma < 0.85:
            action = "excite"
            magnitude = min(abs(mod), 0.05)
            reason = f"gamma={gamma:.3f} below metastable band"
        else:
            action = "maintain"
            magnitude = 0.0
            reason = f"gamma={gamma:.3f} within metastable band"

        return InterventionSuggestion(
            domain=domain,
            action=action,
            magnitude=magnitude,
            reason=reason,
            ssi_domain="EXTERNAL",
        )

    def export_bundle(self, fmt: str = "json") -> bytes:
        """Export evidence bundle for external audit."""
        proof = self._engine.export_proof()
        if fmt == "json":
            return json.dumps(proof, indent=2, default=str, ensure_ascii=False).encode("utf-8")
        raise ValueError(f"Unsupported format: {fmt}")

    @staticmethod
    def _get_git_sha() -> str:
        try:
            result = subprocess.run(  # nosec B603 B607 — hardcoded git command, no user input
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"
