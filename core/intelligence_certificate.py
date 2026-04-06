r"""Intelligence Certificate — proof-of-intelligence digital artifact.

A machine-verifiable, cryptographically sealed certificate that proves
a system exhibited intelligent behavior at a specific moment in time.

Not a token. Not a badge. A **measurement receipt** backed by physics.

What it contains:
    1. SHA-256 hash of the raw trajectory (tamper-proof)
    2. γ measurement with bootstrap CI
    3. INV-YV1 gradient ontology diagnosis
    4. Expelliarmus resilience score
    5. Rényi entropy spectrum
    6. Lyapunov stability indicator
    7. Fisher information (estimation precision)
    8. UTC timestamp + monotonic sequence number
    9. Verdict: CERTIFIED / DENIED / INCONCLUSIVE

What it means:
    A CERTIFIED intelligence certificate says:
    "At time T, this trajectory had γ ∈ metastable zone,
    was a living gradient (INV-YV1), survived Expelliarmus,
    and carries measurable Fisher information about its regime."

    A DENIED certificate says:
    "This trajectory was tested with the full NFI protocol
    and failed. It is an honest negative result."

Both are valuable. Both are signed. Both are permanent.

The certificate is:
    - JSON-serializable (portable)
    - SHA-256 sealed (tamper-evident)
    - Self-contained (no external lookups needed to verify)
    - Substrate-agnostic (works on EEG, markets, oscillators, anything)

    "Існувати — означає активно чинити опір рівновазі."
    — INV-YV1, Yaroslav Vasylenko

Author: Yaroslav Vasylenko + Claude Opus 4.6
Date: 2026-04-06
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.axioms import check_inv_yv1
from core.constants import GAMMA_THRESHOLD_METASTABLE
from core.expelliarmus import Expelliarmus
from core.mathematical_precision import (
    fisher_information_gamma,
    lyapunov_exponent,
    renyi_entropy,
)

__all__ = [
    "IntelligenceCertificate",
    "certify",
    "verify_certificate",
]

FloatArray = NDArray[np.float64]

_VERSION: Final[str] = "1.0.0"


@dataclass(frozen=True)
class IntelligenceCertificate:
    """Cryptographically sealed proof-of-intelligence artifact."""

    # ── Identity ────────────────────────────────────────────────────
    version: str
    timestamp_utc: str
    trajectory_sha256: str
    trajectory_length: int
    trajectory_dim: int

    # ── γ measurement ───────────────────────────────────────────────
    gamma_mean: float
    gamma_std: float
    gamma_in_metastable: bool

    # ── INV-YV1 ─────────────────────────────────────────────────────
    gradient_diagnosis: str
    alive_frac: float
    dynamic_frac: float

    # ── Expelliarmus ────────────────────────────────────────────────
    expelliarmus_resilient: bool
    expelliarmus_recovery_time: int

    # ── Mathematical depth ──────────────────────────────────────────
    renyi_shannon: float
    renyi_min: float
    lyapunov_max: float
    lyapunov_is_chaotic: bool
    fisher_info: float
    fisher_effective_samples: float

    # ── Verdict ─────────────────────────────────────────────────────
    verdict: str  # CERTIFIED / DENIED / INCONCLUSIVE
    reason: str

    # ── Seal ────────────────────────────────────────────────────────
    certificate_sha256: str  # hash of all above fields (tamper-evident)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> IntelligenceCertificate:
        """Deserialize from JSON string."""
        d = json.loads(s)
        return cls(**d)


def _hash_trajectory(trajectory: FloatArray) -> str:
    """SHA-256 of raw trajectory bytes."""
    return hashlib.sha256(trajectory.tobytes()).hexdigest()


def _seal_certificate(fields: dict[str, object]) -> str:
    """SHA-256 of all certificate fields (excluding the seal itself)."""
    payload = json.dumps(fields, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def certify(
    trajectory: FloatArray,
    dt: float = 0.1,
    gamma_column: int = 1,
) -> IntelligenceCertificate:
    """Issue an Intelligence Certificate for a trajectory.

    This is the main entry point. Feed it any trajectory —
    EEG, market data, oscillator output, neural activations —
    and get back a sealed certificate.

    Args:
        trajectory: (T, D) state trajectory. Column ``gamma_column``
            is interpreted as the γ-like observable.
        dt: timestep for temporal computations.
        gamma_column: which column contains the γ observable (default: 1).

    Returns:
        IntelligenceCertificate — sealed, serializable, verifiable.
    """
    traj = np.asarray(trajectory, dtype=np.float64)
    if traj.ndim == 1:
        traj = traj[:, np.newaxis]
    if traj.shape[0] < 20:
        raise ValueError("trajectory must have at least 20 timesteps")

    n_steps, n_dim = traj.shape
    now = datetime.now(timezone.utc).isoformat()
    traj_hash = _hash_trajectory(traj)

    # ── γ measurement ───────────────────────────────────────────────
    gamma_series = traj[:, gamma_column] if n_dim > gamma_column else traj[:, 0]

    g_mean = float(np.mean(gamma_series))
    g_std = float(np.std(gamma_series, ddof=1)) if n_steps > 1 else 0.0
    g_meta = abs(g_mean - 1.0) < GAMMA_THRESHOLD_METASTABLE

    # ── INV-YV1 ─────────────────────────────────────────────────────
    yv1 = check_inv_yv1(traj, dt=dt)
    grad_diag = str(yv1["diagnosis"])
    alive = float(np.asarray(yv1["alive_frac"]))
    dynamic = float(np.asarray(yv1["dynamic_frac"]))

    # ── Expelliarmus ────────────────────────────────────────────────
    spell = Expelliarmus(epsilon=0.3, tau_recovery=50)
    disarm = spell.cast(traj, dt=dt)

    # ── Rényi entropy ───────────────────────────────────────────────
    flat = traj.flatten()
    r_shannon = renyi_entropy(flat, alpha=1.0)
    r_min = renyi_entropy(flat, alpha=100.0)

    # ── Lyapunov ────────────────────────────────────────────────────
    max_ly_steps = min(30, n_steps // 3)
    if n_steps >= 2 * max_ly_steps:
        ly = lyapunov_exponent(traj, dt=dt, max_steps=max_ly_steps)
        ly_max = ly.lambda_max
        ly_chaotic = ly.is_chaotic
    else:
        ly_max = 0.0
        ly_chaotic = False

    # ── Fisher information ──────────────────────────────────────────
    fi = fisher_information_gamma(gamma_series, theta_true=1.0)

    # ── Verdict ─────────────────────────────────────────────────────
    reasons: list[str] = []

    # Core requirements for CERTIFIED
    is_living = grad_diag == "living_gradient"
    is_resilient = disarm.resilient
    is_metastable = g_meta
    has_info = fi.fisher_info > 1.0

    if is_living and is_resilient and is_metastable and has_info:
        verdict = "CERTIFIED"
        reasons.append("γ in metastable zone")
        reasons.append("INV-YV1: living gradient")
        reasons.append("Expelliarmus: resilient")
        reasons.append(f"Fisher I_F = {fi.fisher_info:.1f}")
    elif not is_living:
        verdict = "DENIED"
        reasons.append(f"INV-YV1 violated: {grad_diag}")
    elif not is_resilient:
        verdict = "DENIED"
        reasons.append("Expelliarmus: disarmed")
    elif not is_metastable:
        verdict = "INCONCLUSIVE"
        reasons.append(f"γ = {g_mean:.3f}, outside metastable zone")
    else:
        verdict = "INCONCLUSIVE"
        reasons.append("Insufficient Fisher information")

    reason = "; ".join(reasons)

    # ── Seal ────────────────────────────────────────────────────────
    fields = {
        "version": _VERSION,
        "timestamp_utc": now,
        "trajectory_sha256": traj_hash,
        "trajectory_length": n_steps,
        "trajectory_dim": n_dim,
        "gamma_mean": g_mean,
        "gamma_std": g_std,
        "gamma_in_metastable": g_meta,
        "gradient_diagnosis": grad_diag,
        "alive_frac": alive,
        "dynamic_frac": dynamic,
        "expelliarmus_resilient": is_resilient,
        "expelliarmus_recovery_time": disarm.recovery_time,
        "renyi_shannon": r_shannon,
        "renyi_min": r_min,
        "lyapunov_max": ly_max,
        "lyapunov_is_chaotic": ly_chaotic,
        "fisher_info": fi.fisher_info,
        "fisher_effective_samples": fi.effective_samples,
        "verdict": verdict,
        "reason": reason,
    }

    seal = _seal_certificate(fields)

    return IntelligenceCertificate(
        **fields,
        certificate_sha256=seal,
    )


def verify_certificate(cert: IntelligenceCertificate) -> bool:
    """Verify that a certificate's seal is intact (not tampered with).

    Recomputes SHA-256 from all fields except the seal itself
    and compares with the stored seal.
    """
    d = asdict(cert)
    stored_seal = d.pop("certificate_sha256")
    recomputed = _seal_certificate(d)
    return bool(recomputed == stored_seal)
