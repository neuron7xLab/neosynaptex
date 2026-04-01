"""NFIClosureLoop — one-step closure cycle between CA1-LAM and MFN+.

Pipeline (strict order):
    step 1: MFNSnapshot <- observe(field_sequence)
    step 2: ca1_buffer.push(snapshot)
    step 3: coherence = ca1_buffer.coherence_score()
    step 4: gnc_state = gnc_bridge.update(snapshot, coherence)
    step 5: contract = NFIStateContract(snapshot, gnc_state, ca1_buffer, coherence)
    step 6: return contract

Invariant: no computation of gamma anywhere in this module.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.tau_control.types import MFNSnapshot
from mycelium_fractal_net.types.field import FieldSequence

from .ca1_lam import CA1TemporalBuffer
from .contract import NFIStateContract


def _observe_snapshot(seq: FieldSequence) -> MFNSnapshot:
    """Extract MFNSnapshot from a FieldSequence.

    Reads free_energy, betti_0, d_box from the final field state.
    """
    field = seq.field

    # Free energy: gradient-based energy (sum of squared spatial gradients)
    # More discriminative across seeds than variance — captures spatial structure
    grad_y = np.diff(field, axis=0)
    grad_x = np.diff(field, axis=1)
    free_energy = float(np.sum(grad_y ** 2) + np.sum(grad_x ** 2))

    # Betti-0: connected components via threshold
    # APPROXIMATION: binary threshold at mean, then label counting
    binary = field > np.mean(field)
    from scipy import ndimage
    labeled, betti_0 = ndimage.label(binary)

    # D_box: box-counting dimension
    from mycelium_fractal_net.analytics import compute_box_counting_dimension
    d_box = compute_box_counting_dimension(field)

    state_vector = np.array([free_energy, float(betti_0), d_box], dtype=np.float64)

    return MFNSnapshot(
        state_vector=state_vector,
        free_energy=free_energy,
        betti_0=betti_0,
        d_box=d_box,
    )


class _GNCCoherenceBridge:
    """Minimal bridge: updates GNC state informed by coherence.

    # NFI_PATCH: This wraps GNCState.default() and adjusts modulators
    # based on coherence, without modifying gnc_gamma_bridge.py.
    # coherence -> stability axis (GABA), precision axis (ACh).
    """

    def __init__(self) -> None:
        self._ema_coherence: float | None = None
        self._momentum = 0.7  # EMA momentum: prevents instant convergence

    def update(self, snapshot: MFNSnapshot, coherence: float) -> object:
        """Return a GNCState reflecting current snapshot + coherence.

        Uses EMA-smoothed coherence to prevent instant theta convergence.
        High coherence -> elevated GABA (stability) + ACh (precision).
        Low coherence -> elevated NA (salience) + Glu (plasticity).
        Snapshot free_energy drives Dopamine axis (reward signal).
        """
        from mycelium_fractal_net.neurochem.gnc import GNCState

        # EMA smoothing: prevents single-step convergence
        if self._ema_coherence is None:
            self._ema_coherence = coherence
        else:
            self._ema_coherence = (
                self._momentum * self._ema_coherence
                + (1.0 - self._momentum) * coherence
            )
        coh = self._ema_coherence

        # NFI_PATCH: coherence + snapshot-driven modulator bias
        # NFI_PATCH: wide-amplitude modulation for meaningful theta variation.
        # GNC _compute_theta multiplies deviation by 0.3 (SIGMA), so we need
        # modulator levels far enough from 0.5 to produce visible theta shifts.
        import numpy as np

        # Snapshot-driven: gradient energy modulates DA (reward signal)
        fe = snapshot.free_energy if snapshot.free_energy is not None else 1.0
        da_signal = float(np.clip(0.5 + 0.4 * np.tanh((fe - 5.0) / 10.0), 0.1, 0.9))

        # Betti-0: topological complexity → Serotonin (restraint)
        b0 = float(snapshot.betti_0) if snapshot.betti_0 is not None else 10.0
        ht_signal = float(np.clip(0.5 + 0.35 * np.tanh((b0 - 15.0) / 8.0), 0.15, 0.85))

        # Coherence-driven axes — full [0.1, 0.9] swing
        coh_dev = (coh - 0.5) * 0.8

        levels = {
            "Glutamate": float(np.clip(0.5 - coh_dev, 0.1, 0.9)),
            "GABA": float(np.clip(0.5 + coh_dev, 0.1, 0.9)),
            "Noradrenaline": float(np.clip(0.5 - coh_dev * 0.7, 0.1, 0.9)),
            "Serotonin": ht_signal,
            "Dopamine": da_signal,
            "Acetylcholine": float(np.clip(0.5 + coh_dev * 0.6, 0.1, 0.9)),
            "Opioid": float(np.clip(0.5 + coh_dev * 0.3, 0.1, 0.9)),
        }

        return GNCState.from_levels(levels)


class NFIClosureLoop:
    """One-step closure loop: FieldSequence -> NFIStateContract.

    Usage:
        loop = NFIClosureLoop()
        contract = loop.step(field_sequence)
    """

    def __init__(self, ca1_capacity: int = 64) -> None:
        self._ca1 = CA1TemporalBuffer(capacity=ca1_capacity)
        self._gnc_bridge = _GNCCoherenceBridge()

    @property
    def ca1_buffer(self) -> CA1TemporalBuffer:
        return self._ca1

    def step(self, seq: FieldSequence) -> NFIStateContract:
        """Execute one closure cycle. Strict pipeline order."""
        # step 1: observe
        snapshot = _observe_snapshot(seq)

        # step 2: push to temporal buffer
        self._ca1.push(snapshot)

        # step 3: compute coherence from trajectory
        coherence = self._ca1.coherence_score()

        # step 4: update GNC state via coherence bridge
        gnc_state = self._gnc_bridge.update(snapshot, coherence)

        # step 5: assemble contract
        contract = NFIStateContract(
            mfn_snapshot=snapshot,
            modulation=gnc_state,
            temporal=self._ca1,
            coherence=coherence,
        )

        # step 6: return (no gamma computation here)
        return contract
