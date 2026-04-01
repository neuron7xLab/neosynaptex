from __future__ import annotations

import inspect
import secrets
from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np

from ..cognition.moral_filter_v2 import MoralFilterV2
from ..config.policy_drift import check_policy_drift
from ..memory.multi_level_memory import MultiLevelSynapticMemory
from ..memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory
from ..observability.policy_drift_telemetry import (
    record_policy_catalog_status,
    record_policy_registry_status,
)
from ..rhythm.cognitive_rhythm import CognitiveRhythm


@dataclass(frozen=True)
class Capability:
    """Capability token for authorized kernel mutation."""

    perms: frozenset[str]
    kernel_nonce_hash: str


class MoralRO:
    """Read-only proxy for MoralFilterV2."""

    def __init__(self, moral: MoralFilterV2) -> None:
        self._moral = moral

    @property
    def threshold(self) -> float:
        return self._moral.threshold

    @property
    def ema_accept_rate(self) -> float:
        return self._moral.ema_accept_rate

    def evaluate(self, moral_value: float) -> bool:
        return self._moral.evaluate(moral_value)

    def compute_moral_value(self, *args: Any, **kwargs: Any) -> float:
        return self._moral.compute_moral_value(*args, **kwargs)

    def get_state(self) -> dict[str, Any]:
        return self._moral.get_state()

    def get_current_threshold(self) -> float:
        return self._moral.get_current_threshold()

    def get_ema_value(self) -> float:
        return self._moral.get_ema_value()


class SynapticRO:
    """Read-only proxy for MultiLevelSynapticMemory."""

    def __init__(self, synaptic: MultiLevelSynapticMemory) -> None:
        self._synaptic = synaptic

    def state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self._synaptic.state()

    def get_state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self._synaptic.state()

    @property
    def lambda_l1(self) -> float:
        return self._synaptic.lambda_l1

    @property
    def lambda_l2(self) -> float:
        return self._synaptic.lambda_l2

    @property
    def lambda_l3(self) -> float:
        return self._synaptic.lambda_l3

    @property
    def theta_l1(self) -> float:
        return self._synaptic.theta_l1

    @property
    def theta_l2(self) -> float:
        return self._synaptic.theta_l2

    @property
    def gating12(self) -> float:
        return self._synaptic.gating12

    @property
    def gating23(self) -> float:
        return self._synaptic.gating23

    def memory_usage_bytes(self) -> int:
        return self._synaptic.memory_usage_bytes()

    def to_dict(self) -> dict[str, Any]:
        return self._synaptic.to_dict()


class PelmRO:
    """Read-only proxy for PhaseEntangledLatticeMemory."""

    def __init__(self, pelm: PhaseEntangledLatticeMemory) -> None:
        self._pelm = pelm

    def retrieve(self, *args: Any, **kwargs: Any) -> Any:
        return self._pelm.retrieve(*args, **kwargs)

    def get_state_stats(self) -> dict[str, Any]:
        return self._pelm.get_state_stats()

    def memory_usage_bytes(self) -> int:
        return self._pelm.memory_usage_bytes()

    @property
    def capacity(self) -> int:
        return self._pelm.capacity

    @property
    def size(self) -> int:
        return self._pelm.size

    def detect_corruption(self) -> bool:
        return self._pelm.detect_corruption()


class RhythmRO:
    """Read-only proxy for CognitiveRhythm."""

    def __init__(self, rhythm: CognitiveRhythm) -> None:
        self._rhythm = rhythm

    @property
    def phase(self) -> str:
        return self._rhythm.phase

    @property
    def counter(self) -> int:
        return self._rhythm.counter

    def is_wake(self) -> bool:
        return self._rhythm.is_wake()

    def is_sleep(self) -> bool:
        return self._rhythm.is_sleep()

    def get_state_label(self) -> str:
        return self._rhythm.get_state_label()

    @property
    def wake_duration(self) -> int:
        return self._rhythm.wake_duration

    @property
    def sleep_duration(self) -> int:
        return self._rhythm.sleep_duration

    def get_current_phase(self) -> str:
        return self._rhythm.get_current_phase()


class GovernanceKernel:
    """Single mutation boundary for cognitive state."""

    def __init__(
        self,
        *,
        dim: int,
        capacity: int,
        wake_duration: int,
        sleep_duration: int,
        initial_moral_threshold: float | None = None,
        synaptic_config: Any | None = None,
    ) -> None:
        self._lock = RLock()
        self._dim = dim
        self._capacity = capacity
        self._wake_duration = wake_duration
        self._sleep_duration = sleep_duration
        self._initial_moral_threshold = initial_moral_threshold
        self._synaptic_config = synaptic_config

        # Generate capability nonce for authorization
        self._cap_nonce = secrets.token_bytes(32)
        self._cap_hash = sha256(self._cap_nonce).hexdigest()

        self._moral: MoralFilterV2
        self._synaptic: MultiLevelSynapticMemory
        self._pelm: PhaseEntangledLatticeMemory
        self._rhythm: CognitiveRhythm
        self._initialize_components()

    def _initialize_components(self) -> None:
        status = check_policy_drift(enforce=True)
        record_policy_registry_status(
            policy_name=status.policy_name,
            policy_hash=status.policy_hash,
            policy_contract_version=status.policy_contract_version,
            registry_hash=status.registry_hash,
            registry_signature_valid=status.registry_signature_valid,
            drift_detected=status.drift_detected,
            reason=";".join(status.errors) if status.errors else None,
        )
        record_policy_catalog_status(
            policy_name=status.policy_name,
            policy_contract_version=status.policy_contract_version,
            catalog_hash=status.catalog_hash,
            catalog_signature_valid=status.catalog_signature_valid,
            drift_detected=status.drift_detected,
            reason=";".join(status.errors) if status.errors else None,
        )
        self._moral = MoralFilterV2(initial_threshold=self._initial_moral_threshold)
        self._synaptic = MultiLevelSynapticMemory(dimension=self._dim, config=self._synaptic_config)
        self._pelm = PhaseEntangledLatticeMemory(dimension=self._dim, capacity=self._capacity)
        self._rhythm = CognitiveRhythm(
            wake_duration=self._wake_duration, sleep_duration=self._sleep_duration
        )
        self._refresh_proxies()

    def _refresh_proxies(self) -> None:
        self.moral_ro = MoralRO(self._moral)
        self.synaptic_ro = SynapticRO(self._synaptic)
        self.pelm_ro = PelmRO(self._pelm)
        self.rhythm_ro = RhythmRO(self._rhythm)

    def _assert_can_mutate(self, required_perm: str, cap: Capability | None) -> None:
        """Validate capability for kernel mutation.

        Args:
            required_perm: Permission required for the operation.
            cap: Capability token, or None for internal allowlist check.

        Raises:
            PermissionError: If caller is not authorized.
        """
        if cap is not None:
            if cap.kernel_nonce_hash != self._cap_hash:
                raise PermissionError("Invalid capability: nonce mismatch")
            if required_perm not in cap.perms:
                raise PermissionError(f"Capability missing permission: {required_perm}")
            return

        # cap is None => allow ONLY internal modules:
        caller = inspect.stack()[2].frame.f_globals.get("__name__", "")
        ALLOWLIST = {"mlsdm.core.cognitive_controller", "mlsdm.core.llm_wrapper"}
        if caller not in ALLOWLIST:
            raise PermissionError(f"Kernel mutation blocked from {caller}")

    def moral_adapt(self, accepted: bool, *, cap: Capability | None = None) -> None:
        self._assert_can_mutate("MUTATE_MORAL_THRESHOLD", cap)
        with self._lock:
            self._moral.adapt(accepted)

    def memory_commit(
        self, prompt_vector: np.ndarray, phase: float, *, provenance: Any | None = None, cap: Capability | None = None
    ) -> None:
        self._assert_can_mutate("MEMORY_COMMIT", cap)
        with self._lock:
            self._synaptic.update(prompt_vector)
            self._pelm.entangle(prompt_vector.tolist(), phase=phase, provenance=provenance)

    def rhythm_step(self) -> None:
        with self._lock:
            self._rhythm.step()

    def issue_capability(self, perms: set[str]) -> Capability:
        """Issue a capability token for authorized mutation.

        Args:
            perms: Set of permissions to grant.

        Returns:
            Capability token with requested permissions.

        Raises:
            PermissionError: If caller is not in the internal allowlist.
        """
        # only allow internal allowlist caller
        caller = inspect.stack()[1].frame.f_globals.get("__name__", "")
        ALLOWLIST = {"mlsdm.core.cognitive_controller", "mlsdm.core.llm_wrapper"}
        if caller not in ALLOWLIST:
            raise PermissionError(f"Cannot issue capability from {caller}")
        return Capability(perms=frozenset(perms), kernel_nonce_hash=self._cap_hash)

    def reset(
        self,
        *,
        dim: int | None = None,
        capacity: int | None = None,
        wake_duration: int | None = None,
        sleep_duration: int | None = None,
        initial_moral_threshold: float | None = None,
        synaptic_config: Any | None = None,
    ) -> None:
        with self._lock:
            self._dim = dim if dim is not None else self._dim
            self._capacity = capacity if capacity is not None else self._capacity
            self._wake_duration = (
                wake_duration if wake_duration is not None else self._wake_duration
            )
            self._sleep_duration = (
                sleep_duration if sleep_duration is not None else self._sleep_duration
            )
            if initial_moral_threshold is not None:
                self._initial_moral_threshold = initial_moral_threshold
            if synaptic_config is not None:
                self._synaptic_config = synaptic_config
            self._initialize_components()
