"""Simulation entrypoints: simulate(), simulate_batch(), simulate_history()."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.core.engine import (
    run_mycelium_simulation,
    run_mycelium_simulation_with_history,
)
from mycelium_fractal_net.core.types import SimulationConfig
from mycelium_fractal_net.types.field import (
    FieldSequence,
    GABAATonicSpec,
    NeuromodulationSpec,
    NeuromodulationStateSnapshot,
    ObservationNoiseSpec,
    SerotonergicPlasticitySpec,
    SimulationSpec,
)

if TYPE_CHECKING:
    from collections.abc import Iterable



__all__ = ['cleanup_history_memmap', 'simulate_batch', 'simulate_final', 'simulate_history', 'simulate_null', 'simulate_scenario']

def _fingerprint(spec: SimulationSpec) -> str:
    return hashlib.sha256(
        json.dumps(spec.as_runtime_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def _metadata(spec: SimulationSpec) -> dict[str, object]:
    return {
        "seed": spec.seed,
        "config_fingerprint": _fingerprint(spec),
        "reproducible": True,
    }


def _to_config(spec: SimulationSpec) -> SimulationConfig:
    return SimulationConfig(**spec.as_runtime_dict())


def _extract_neuromod_snapshot(meta: dict[str, Any]) -> NeuromodulationStateSnapshot | None:
    """Build typed snapshot from engine metadata if neuromodulation ran."""
    state = meta.get("neuromodulation_state")
    if state and isinstance(state, dict):
        try:
            return NeuromodulationStateSnapshot.from_dict(state)
        except (ValueError, KeyError) as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to build NeuromodulationStateSnapshot from engine metadata: %s", exc
            )
    # Fall back to mean-level metrics
    if (
        meta.get("plasticity_index_mean", 0.0) != 0.0
        or meta.get("effective_inhibition_mean", 0.0) != 0.0
    ):
        return NeuromodulationStateSnapshot(
            plasticity_index=float(meta.get("plasticity_index_mean", 0.0)),
            effective_inhibition=float(meta.get("effective_inhibition_mean", 0.0)),
            effective_gain=float(meta.get("effective_gain_mean", 0.0)),
            observation_noise_gain=float(meta.get("observation_noise_gain_mean", 0.0)),
        )
    return None


def _persist_history_memmap(
    history: np.ndarray, history_dir: str | Path | None = None
) -> tuple[np.memmap, str]:
    target_dir = (
        Path(history_dir)
        if history_dir is not None
        else Path(tempfile.mkdtemp(prefix="mfn-history-"))
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "history.memmap.npy"
    mm = np.lib.format.open_memmap(path, mode="w+", dtype=np.float64, shape=history.shape)
    mm[:] = history.astype(np.float64, copy=False)
    mm.flush()
    del mm  # Close the write handle to prevent fd leak
    readonly = np.load(path, mmap_mode="r")
    return readonly, str(path)


def cleanup_history_memmap(memmap_path: str | Path) -> None:
    """Clean up memmap history file and its parent temp directory.

    Call this when the FieldSequence is no longer needed to prevent
    /tmp accumulation under sustained load.
    """
    import shutil

    p = Path(memmap_path)
    if p.exists():
        p.unlink(missing_ok=True)
    parent = p.parent
    if parent.name.startswith("mfn-history-") and parent.exists():
        shutil.rmtree(parent, ignore_errors=True)


def simulate_final(spec: SimulationSpec) -> FieldSequence:
    result = run_mycelium_simulation(_to_config(spec))
    metadata = dict(result.metadata)
    metadata.update(_metadata(spec))
    neuro_snap = _extract_neuromod_snapshot(metadata)
    return FieldSequence(
        field=result.field,
        history=None,
        spec=spec,
        neuromodulation_state=neuro_snap,
        metadata=metadata,
    )


def simulate_history(
    spec: SimulationSpec,
    *,
    history_backend: str = "memory",
    history_dir: str | Path | None = None,
) -> FieldSequence:
    result = run_mycelium_simulation_with_history(_to_config(spec))
    metadata = dict(result.metadata)
    metadata.update(_metadata(spec))
    history = result.history
    if history is None:
        raise RuntimeError("simulation did not return history")
    if history_backend == "memmap":
        history_memmap, memmap_path = _persist_history_memmap(history, history_dir=history_dir)
        metadata.update(
            {
                "history_backend": "memmap",
                "history_memmap_path": memmap_path,
                "history_cleanup_policy": "caller_removes_temp_path",
            }
        )
        history_value: np.ndarray = history_memmap
    else:
        metadata["history_backend"] = "memory"
        history_value = history
    neuro_snap = _extract_neuromod_snapshot(metadata)
    return FieldSequence(
        field=result.field,
        history=history_value,
        spec=spec,
        neuromodulation_state=neuro_snap,
        metadata=metadata,
    )


def simulate_batch(
    specs: Iterable[SimulationSpec], with_history: bool = False
) -> list[FieldSequence]:
    fn = simulate_history if with_history else simulate_final
    return [fn(spec) for spec in specs]


def simulate_scenario(name: str) -> FieldSequence:
    scenario_specs = {
        "synthetic_morphology": SimulationSpec(
            grid_size=32, steps=24, seed=42, alpha=0.16, spike_probability=0.22
        ),
        "sensor_grid_anomaly": SimulationSpec(
            grid_size=32,
            steps=24,
            seed=77,
            alpha=0.12,
            spike_probability=0.35,
            neuromodulation=NeuromodulationSpec(
                profile="observation_noise_gaussian_temporal",
                enabled=True,
                dt_seconds=1.0,
                observation_noise=ObservationNoiseSpec(
                    profile="observation_noise_gaussian_temporal",
                    std=0.0012,
                    temporal_smoothing=0.35,
                ),
            ),
        ),
        "regime_transition": SimulationSpec(
            grid_size=32,
            steps=28,
            seed=91,
            alpha=0.20,
            spike_probability=0.28,
            neuromodulation=NeuromodulationSpec(
                profile="serotonergic_reorganization_candidate",
                enabled=True,
                dt_seconds=1.0,
                serotonergic=SerotonergicPlasticitySpec(
                    profile="serotonergic_reorganization_candidate",
                    gain_fluidity_coeff=0.08,
                    reorganization_drive=0.12,
                    coherence_bias=0.02,
                ),
            ),
        ),
        "balanced_criticality": SimulationSpec(
            grid_size=32,
            steps=28,
            seed=113,
            alpha=0.18,
            spike_probability=0.25,
            neuromodulation=NeuromodulationSpec(
                profile="balanced_criticality_candidate",
                enabled=True,
                dt_seconds=1.0,
                intrinsic_field_jitter=True,
                intrinsic_field_jitter_var=0.0002,
                gabaa_tonic=GABAATonicSpec(
                    profile="balanced_criticality_candidate",
                    agonist_concentration_um=0.2,
                    resting_affinity_um=0.25,
                    active_affinity_um=0.22,
                    desensitization_rate_hz=0.015,
                    recovery_rate_hz=0.03,
                    shunt_strength=0.18,
                ),
                serotonergic=SerotonergicPlasticitySpec(
                    profile="balanced_criticality_candidate",
                    gain_fluidity_coeff=0.05,
                    reorganization_drive=0.05,
                    coherence_bias=0.01,
                ),
            ),
        ),
        "inhibitory_stabilization": SimulationSpec(
            grid_size=32,
            steps=24,
            seed=131,
            alpha=0.18,
            spike_probability=0.20,
            neuromodulation=NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
                dt_seconds=1.0,
                gabaa_tonic=GABAATonicSpec(
                    profile="gabaa_tonic_muscimol_alpha1beta3",
                    agonist_concentration_um=0.85,
                    resting_affinity_um=0.45,
                    active_affinity_um=0.35,
                    desensitization_rate_hz=0.05,
                    recovery_rate_hz=0.02,
                    shunt_strength=0.42,
                ),
            ),
        ),
        "high_inhibition_recovery": SimulationSpec(
            grid_size=32,
            steps=28,
            seed=133,
            alpha=0.18,
            spike_probability=0.18,
            neuromodulation=NeuromodulationSpec(
                profile="gabaa_tonic_extrasynaptic_delta_high_affinity",
                enabled=True,
                dt_seconds=1.0,
                gabaa_tonic=GABAATonicSpec(
                    profile="gabaa_tonic_extrasynaptic_delta_high_affinity",
                    agonist_concentration_um=0.35,
                    resting_affinity_um=0.10,
                    active_affinity_um=0.08,
                    desensitization_rate_hz=0.02,
                    recovery_rate_hz=0.06,
                    shunt_strength=0.50,
                    rest_offset_mv=-0.40,
                    baseline_activation_offset_mv=-0.15,
                    tonic_inhibition_scale=1.25,
                    k_on=0.30,
                    k_off=0.04,
                    K_R=0.10,
                    c=0.95,
                    Q=0.88,
                    L=1.45,
                    binding_sites=3,
                    k_leak_reduction_fraction=0.24,
                ),
            ),
        ),
    }
    if name not in scenario_specs:
        raise ValueError(f"Unknown scenario {name!r}. Available: {sorted(scenario_specs)}")
    return simulate_history(scenario_specs[name])


def simulate_null(mode: str = "uniform", grid_size: int = 32, steps: int = 30) -> FieldSequence:
    """Generate a null-mode FieldSequence for invariant validation.

    Null modes are systems where Λ₅ should be trivially 0 or degenerate.
    Use to validate that the invariant operator is working correctly.

    Modes:
        'uniform':   constant field, no structure → Λ₅ = 0
        'static':    random field, no dynamics → Λ₅ = 0
        'diffusion': pure diffusion, no reaction → Λ₅ > 0 but no pattern
        'noise':     white noise per step → Λ₅ undefined (no coherence)
    """
    N = grid_size
    T = steps

    if mode == "uniform":
        field = np.full((N, N), 0.5, dtype=np.float64)
        history = np.stack([field] * T)
    elif mode == "static":
        field = np.random.default_rng(42).uniform(0, 1, (N, N))
        history = np.stack([field] * T)
    elif mode == "diffusion":
        rng = np.random.default_rng(42)
        history = np.zeros((T, N, N), dtype=np.float64)
        history[0] = rng.normal(-0.07, 0.005, (N, N))
        for t in range(1, T):
            f = history[t - 1]
            lap = (
                np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1) - 4 * f
            )
            history[t] = f + 0.18 * lap
    elif mode == "noise":
        rng = np.random.default_rng(42)
        history = rng.uniform(0, 1, (T, N, N))
    else:
        raise ValueError(f"Unknown null mode {mode!r}. Use: uniform, static, diffusion, noise")

    return FieldSequence(
        field=history[-1],
        history=history,
        spec=None,
        metadata={"null_mode": mode, "grid_size": N, "steps": T},
    )
