import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import numpy as np

from mlsdm.cognition.moral_filter import MoralFilter
from mlsdm.cognition.ontology_matcher import OntologyMatcher
from mlsdm.config.policy_drift import get_policy_snapshot
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.provenance import MemoryProvenance, MemorySource
from mlsdm.memory.qilm_module import QILM
from mlsdm.memory.store import MemoryItem, MemoryStore, compute_content_hash
from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm
from mlsdm.utils.data_serializer import DataSerializer
from mlsdm.utils.errors import (
    ConfigurationError,
    StateCorruptError,
    StateFileNotFoundError,
    StateIncompleteError,
    StateVersionMismatchError,
)
from mlsdm.utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

# Current state format version - increment only when changing the schema
STATE_FORMAT_VERSION = 1

# Registry of migration functions: (from_version, to_version) -> migration_fn
# Migration functions take data dict and return migrated data dict
_MIGRATION_REGISTRY: dict[tuple[int, int], Callable[[dict[str, Any]], dict[str, Any]]] = {}


def register_migration(
    from_version: int, to_version: int
) -> Callable[[Callable[[dict[str, Any]], dict[str, Any]]], Callable[[dict[str, Any]], dict[str, Any]]]:
    """Decorator to register a state format migration function.

    Args:
        from_version: Source format version
        to_version: Target format version

    Returns:
        Decorator function that registers the migration
    """
    def decorator(
        fn: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        _MIGRATION_REGISTRY[(from_version, to_version)] = fn
        return fn
    return decorator


def _migrate_state(data: dict[str, Any], from_version: int, to_version: int) -> dict[str, Any]:
    """Apply migrations to upgrade state from one version to another.

    Args:
        data: State data to migrate
        from_version: Current format version of the data
        to_version: Target format version

    Returns:
        Migrated state data

    Raises:
        StateVersionMismatchError: If no migration path exists
    """
    current_version = from_version
    migrated_data = data.copy()

    while current_version < to_version:
        next_version = current_version + 1
        migration_key = (current_version, next_version)

        if migration_key not in _MIGRATION_REGISTRY:
            raise StateVersionMismatchError(
                filepath="<in-memory>",
                file_version=from_version,
                current_version=to_version,
                message=(
                    f"No migration path from version {current_version} to {next_version}. "
                    f"Cannot migrate from v{from_version} to v{to_version}."
                ),
            )

        migration_fn = _MIGRATION_REGISTRY[migration_key]
        migrated_data = migration_fn(migrated_data)
        migrated_data["format_version"] = next_version
        current_version = next_version
        logger.info(
            "Migrated state format from v%d to v%d",
            current_version - 1,
            current_version,
        )

    return migrated_data


# Required top-level keys in state file
_REQUIRED_STATE_KEYS = {"memory_state", "qilm"}

# Required keys in memory_state
_REQUIRED_MEMORY_STATE_KEYS = {
    "dimension",
    "lambda_l1",
    "lambda_l2",
    "lambda_l3",
    "theta_l1",
    "theta_l2",
    "gating12",
    "gating23",
    "state_L1",
    "state_L2",
    "state_L3",
}

# Required keys in qilm
_REQUIRED_QILM_KEYS = {"memory", "phases"}


class MemoryManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.dimension = int(config.get("dimension", 10))

        mem_cfg = config.get("multi_level_memory", {})
        self.memory = MultiLevelSynapticMemory(
            dimension=self.dimension,
            lambda_l1=mem_cfg.get("lambda_l1", 0.5),
            lambda_l2=mem_cfg.get("lambda_l2", 0.1),
            lambda_l3=mem_cfg.get("lambda_l3", 0.01),
            theta_l1=mem_cfg.get("theta_l1", 1.0),
            theta_l2=mem_cfg.get("theta_l2", 2.0),
            gating12=mem_cfg.get("gating12", 0.5),
            gating23=mem_cfg.get("gating23", 0.3),
        )

        filt_cfg = config.get("moral_filter", {})
        self.filter = MoralFilter(
            threshold=filt_cfg.get("threshold", 0.5),
            adapt_rate=filt_cfg.get("adapt_rate", 0.05),
            min_threshold=filt_cfg.get("min_threshold", 0.3),
            max_threshold=filt_cfg.get("max_threshold", 0.9),
        )

        onto_cfg = config.get("ontology_matcher", {})
        ontology_vectors = np.array(
            onto_cfg.get("ontology_vectors", np.eye(self.dimension).tolist())
        )
        ontology_labels = onto_cfg.get("ontology_labels")
        self.matcher = OntologyMatcher(ontology_vectors, labels=ontology_labels)

        rhythm_cfg = config.get("cognitive_rhythm", {})
        self.rhythm = CognitiveRhythm(
            wake_duration=rhythm_cfg.get("wake_duration", 5),
            sleep_duration=rhythm_cfg.get("sleep_duration", 2),
        )

        self.qilm = QILM()
        self.metrics_collector = MetricsCollector()
        self.strict_mode = bool(config.get("strict_mode", False))
        self._policy_snapshot = get_policy_snapshot()

        # LTM (Long-Term Memory) store - optional, disabled by default
        self._ltm_store: MemoryStore | None = None
        self._ltm_strict: bool = False
        self._ltm_default_ttl_s: float | None = None
        self._init_ltm_store(config)

    def _init_ltm_store(self, config: dict[str, Any]) -> None:
        """Initialize LTM store if enabled in config.

        LTM is enabled only when:
        - config.memory.ltm_enabled == True
        - config.memory.ltm_backend == "sqlite"
        - A database path is provided (config or env)

        This method never crashes - logs errors and continues without LTM
        unless ltm_strict=True is set.
        """
        memory_cfg = config.get("memory", {})

        # Check if LTM is enabled
        if not memory_cfg.get("ltm_enabled", False):
            return

        # Check backend type
        backend = memory_cfg.get("ltm_backend", "sqlite")
        if backend != "sqlite":
            logger.warning(
                "LTM backend '%s' not supported, only 'sqlite' is available. LTM disabled.",
                backend,
            )
            return

        # Get database path from config or environment
        db_path = memory_cfg.get("ltm_db_path") or os.environ.get("MLSDM_LTM_DB_PATH")
        if not db_path:
            logger.warning(
                "LTM enabled but no database path provided. "
                "Set 'memory.ltm_db_path' in config or MLSDM_LTM_DB_PATH env var. LTM disabled."
            )
            return

        # Check for encryption configuration
        encryption_key: bytes | None = None
        encryption_enabled = (
            os.environ.get("MLSDM_LTM_ENCRYPTION", "0") == "1"
            and os.environ.get("MLSDM_LTM_KEY") is not None
        )

        if encryption_enabled:
            key_hex = os.environ.get("MLSDM_LTM_KEY", "")
            try:
                encryption_key = bytes.fromhex(key_hex)
            except ValueError:
                logger.error("Invalid MLSDM_LTM_KEY format (expected hex). LTM disabled.")
                return

        # Store raw option (default: False, meaning scrubbing enabled)
        store_raw = memory_cfg.get("ltm_store_raw", False)

        # Strict mode for LTM errors
        self._ltm_strict = memory_cfg.get("ltm_strict", False)
        self._ltm_default_ttl_s = memory_cfg.get("ltm_ttl_s")

        # Initialize SQLite store
        try:
            from mlsdm.memory.sqlite_store import SQLiteMemoryStore

            self._ltm_store = SQLiteMemoryStore(
                db_path=db_path,
                encryption_key=encryption_key,
                store_raw=store_raw,
            )
            logger.info(
                "LTM store initialized at %s (encryption=%s, strict=%s)",
                db_path,
                encryption_enabled,
                self._ltm_strict,
            )
        except ConfigurationError:
            # Re-raise configuration errors (e.g., encryption without cryptography)
            raise
        except Exception as e:
            if self._ltm_strict:
                raise
            logger.error("Failed to initialize LTM store: %s. LTM disabled.", e, exc_info=True)

    def _persist_to_ltm(self, content: str, provenance: MemoryProvenance | None = None) -> None:
        """Persist content to long-term memory store.

        This is called after successful memory operations to optionally
        persist to the LTM backend. Errors are logged and do not crash
        the core path unless ltm_strict=True.

        Args:
            content: Text content to persist
            provenance: Optional provenance metadata
        """
        if self._ltm_store is None:
            return

        try:
            policy_hash = self._policy_snapshot.policy_hash
            policy_contract_version = self._policy_snapshot.policy_contract_version
            ttl_s = self._ltm_default_ttl_s
            content_hash = compute_content_hash(content)
            item_ts = time.time()
            retention_expires_at = (
                datetime.fromtimestamp(item_ts + ttl_s) if ttl_s is not None else None
            )
            item = MemoryItem(
                id=str(uuid.uuid4()),
                ts=item_ts,
                content=content,
                content_hash=content_hash,
                ttl_s=ttl_s,
                provenance=(
                    provenance.with_integrity(
                        content_hash=content_hash,
                        policy_hash=policy_hash,
                        policy_contract_version=policy_contract_version,
                        retention_expires_at=retention_expires_at,
                    )
                    if provenance is not None
                    else MemoryProvenance(
                        source=MemorySource.SYSTEM_PROMPT,
                        confidence=1.0,
                        timestamp=datetime.now(),
                        content_hash=content_hash,
                        policy_hash=policy_hash,
                        policy_contract_version=policy_contract_version,
                        retention_expires_at=retention_expires_at,
                    )
                ),
            )
            self._ltm_store.put(item)
            logger.debug("Persisted memory to LTM: %s", item.id)
        except Exception as e:
            if self._ltm_strict:
                raise
            logger.warning("Failed to persist to LTM: %s", e, exc_info=True)

    def _is_sensitive(self, vec: np.ndarray) -> bool:
        if np.linalg.norm(vec) > 10 or np.sum(vec) < 0:
            logger.warning("Sensitive vector detected by heuristic.")
            return True
        return False

    async def process_event(self, event_vector: np.ndarray, moral_value: float) -> None:
        if self.strict_mode and self._is_sensitive(event_vector):
            raise ValueError("Sensitive data detected in strict mode.")

        self.metrics_collector.start_event_timer()

        accepted = self.filter.evaluate(moral_value)
        self.filter.adapt(accepted)

        if not accepted:
            self.metrics_collector.add_latent_event()
            self.metrics_collector.stop_event_timer_and_record_latency()
            return

        self.memory.update(event_vector)
        self.matcher.match(event_vector, metric="cosine")
        self.qilm.entangle_phase(event_vector, phase=self.rhythm.get_current_phase())

        self.metrics_collector.add_accepted_event()
        self.metrics_collector.stop_event_timer_and_record_latency()

        # Optional: Persist to LTM if enabled
        if self._ltm_store is not None:
            # Convert event vector to text representation for LTM
            # For large vectors, truncate to avoid performance issues
            if len(event_vector) <= 10:
                vec_repr = str(event_vector.tolist())
            else:
                # Show first 5 and last 5 elements for large vectors
                first_5 = event_vector[:5].tolist()
                last_5 = event_vector[-5:].tolist()
                vec_repr = f"{first_5}...{last_5}"

            content = f"Event vector (dim={len(event_vector)}): {vec_repr}"
            provenance = MemoryProvenance(
                source=MemorySource.SYSTEM_PROMPT,
                confidence=moral_value,
                timestamp=datetime.now(),
            )
            self._persist_to_ltm(content, provenance)

    async def simulate(self, num_steps: int, event_gen: Iterator[tuple[np.ndarray, float]]) -> None:
        for step, (ev, mv) in enumerate(event_gen):
            if ev.shape[0] != self.dimension:
                raise ValueError("Event dimension mismatch.")
            L1, L2, L3 = self.memory.get_state()
            self.metrics_collector.record_memory_state(
                step, L1, L2, L3, self.rhythm.get_current_phase()
            )
            self.metrics_collector.record_moral_threshold(self.filter.threshold)

            if self.rhythm.is_wake():
                await self.process_event(ev, mv)

            self.rhythm.step()
            await asyncio.sleep(0)

    def run_simulation(
        self, num_steps: int, event_gen: Iterator[tuple[np.ndarray, float]] | None = None
    ) -> None:
        if event_gen is None:

            def default_gen() -> Iterator[tuple[np.ndarray, float]]:
                for _ in range(num_steps):
                    ev = np.random.randn(self.dimension)
                    mv = float(np.clip(np.random.rand(), 0.0, 1.0))
                    yield ev, mv

            event_gen = default_gen()

        asyncio.run(self.simulate(num_steps, event_gen))

    def save_system_state(self, filepath: str) -> None:
        """Save the complete system state to a file.

        The saved state includes:
        - format_version: Schema version for migration support
        - memory_state: Multi-level synaptic memory (L1/L2/L3 and params)
        - qilm: QILM module state (memory vectors and phases)

        Args:
            filepath: Path to save the state file (JSON or NPZ format)

        Raises:
            ValueError: If filepath is not a string
            IOError: If file cannot be written
        """
        data: dict[str, Any] = {
            "format_version": STATE_FORMAT_VERSION,
            "memory_state": self.memory.to_dict(),
            "qilm": self.qilm.to_dict(),
        }
        DataSerializer.save(data, filepath)
        logger.info(
            "Saved system state to %s (format_version=%d)",
            filepath,
            STATE_FORMAT_VERSION,
        )

    def load_system_state(self, filepath: str) -> None:
        """Load and restore the complete system state from a file.

        This method performs full validation of the state file and
        restores the memory and QILM state. The operation is atomic:
        either the entire state is restored successfully, or the
        current state remains unchanged.

        Args:
            filepath: Path to the state file (JSON or NPZ format)

        Raises:
            StateFileNotFoundError: If the file does not exist
            StateCorruptError: If the file is not valid JSON or has malformed data
            StateVersionMismatchError: If the format version cannot be migrated
            StateIncompleteError: If required fields are missing or have wrong types
        """
        # Check file exists
        if not os.path.exists(filepath):
            raise StateFileNotFoundError(filepath)

        # Load and parse data
        try:
            data = DataSerializer.load(filepath)
        except json.JSONDecodeError as e:
            raise StateCorruptError(
                filepath=filepath,
                reason=f"Invalid JSON: {e}",
            ) from e
        except Exception as e:
            raise StateCorruptError(
                filepath=filepath,
                reason=str(e),
            ) from e

        if not isinstance(data, dict):
            raise StateCorruptError(
                filepath=filepath,
                reason=f"Expected dict at root, got {type(data).__name__}",
            )

        # Handle format_version - default to 1 for legacy files without version
        file_version = data.get("format_version", 1)
        if not isinstance(file_version, int):
            raise StateCorruptError(
                filepath=filepath,
                reason=f"format_version must be int, got {type(file_version).__name__}",
            )

        # Check for version from future
        if file_version > STATE_FORMAT_VERSION:
            raise StateVersionMismatchError(
                filepath=filepath,
                file_version=file_version,
                current_version=STATE_FORMAT_VERSION,
                message=(
                    f"State file version {file_version} is newer than "
                    f"current version {STATE_FORMAT_VERSION}. "
                    "Please upgrade MLSDM to load this state file."
                ),
            )

        # Apply migrations if needed
        if file_version < STATE_FORMAT_VERSION:
            try:
                data = _migrate_state(data, file_version, STATE_FORMAT_VERSION)
            except StateVersionMismatchError:
                raise StateVersionMismatchError(
                    filepath=filepath,
                    file_version=file_version,
                    current_version=STATE_FORMAT_VERSION,
                ) from None

        # Validate required top-level keys
        missing_keys = _REQUIRED_STATE_KEYS - set(data.keys())
        if missing_keys:
            raise StateIncompleteError(
                filepath=filepath,
                missing_fields=list(missing_keys),
            )

        # Validate memory_state structure
        memory_state = data["memory_state"]
        if not isinstance(memory_state, dict):
            raise StateCorruptError(
                filepath=filepath,
                reason=f"memory_state must be dict, got {type(memory_state).__name__}",
            )

        missing_memory_keys = _REQUIRED_MEMORY_STATE_KEYS - set(memory_state.keys())
        if missing_memory_keys:
            raise StateIncompleteError(
                filepath=filepath,
                missing_fields=[f"memory_state.{k}" for k in missing_memory_keys],
            )

        # Validate memory_state field types
        invalid_fields: dict[str, str] = {}
        if not isinstance(memory_state.get("dimension"), int):
            invalid_fields["memory_state.dimension"] = "expected int"
        for param in ["lambda_l1", "lambda_l2", "lambda_l3", "theta_l1", "theta_l2", "gating12", "gating23"]:
            val = memory_state.get(param)
            if not isinstance(val, (int, float)):
                invalid_fields[f"memory_state.{param}"] = "expected number"
        for level in ["state_L1", "state_L2", "state_L3"]:
            val = memory_state.get(level)
            if not isinstance(val, list):
                invalid_fields[f"memory_state.{level}"] = "expected list"

        # Validate qilm structure
        qilm_state = data["qilm"]
        if not isinstance(qilm_state, dict):
            raise StateCorruptError(
                filepath=filepath,
                reason=f"qilm must be dict, got {type(qilm_state).__name__}",
            )

        missing_qilm_keys = _REQUIRED_QILM_KEYS - set(qilm_state.keys())
        if missing_qilm_keys:
            raise StateIncompleteError(
                filepath=filepath,
                missing_fields=[f"qilm.{k}" for k in missing_qilm_keys],
            )

        if not isinstance(qilm_state.get("memory"), list):
            invalid_fields["qilm.memory"] = "expected list"
        if not isinstance(qilm_state.get("phases"), list):
            invalid_fields["qilm.phases"] = "expected list"

        qilm_memory = qilm_state.get("memory")
        qilm_phases = qilm_state.get("phases")
        if isinstance(qilm_memory, list):
            for index, vector in enumerate(qilm_memory):
                if not isinstance(vector, list):
                    invalid_fields[f"qilm.memory[{index}]"] = "expected list"
                elif len(vector) != self.dimension:
                    invalid_fields[f"qilm.memory[{index}]"] = (
                        f"length {len(vector)} does not match dimension {self.dimension}"
                    )
        if isinstance(qilm_memory, list) and isinstance(qilm_phases, list):
            if len(qilm_phases) != len(qilm_memory):
                invalid_fields["qilm.phases"] = (
                    f"length {len(qilm_phases)} does not match memory length "
                    f"{len(qilm_memory)}"
                )

        if invalid_fields:
            raise StateIncompleteError(
                filepath=filepath,
                invalid_fields=invalid_fields,
            )

        # Validate dimension consistency
        saved_dim = memory_state["dimension"]
        if saved_dim != self.dimension:
            raise StateIncompleteError(
                filepath=filepath,
                invalid_fields={
                    "memory_state.dimension": (
                        f"saved dimension {saved_dim} does not match "
                        f"current manager dimension {self.dimension}"
                    )
                },
            )

        # Validate L1/L2/L3 vector lengths
        for level_name in ["state_L1", "state_L2", "state_L3"]:
            level_data = memory_state[level_name]
            if len(level_data) != self.dimension:
                raise StateIncompleteError(
                    filepath=filepath,
                    invalid_fields={
                        f"memory_state.{level_name}": (
                            f"length {len(level_data)} does not match "
                            f"dimension {self.dimension}"
                        )
                    },
                )

        # All validation passed - now restore state atomically
        # Create new instances to ensure atomic restoration
        try:
            # Restore memory state
            new_l1 = np.array(memory_state["state_L1"], dtype=np.float32)
            new_l2 = np.array(memory_state["state_L2"], dtype=np.float32)
            new_l3 = np.array(memory_state["state_L3"], dtype=np.float32)

            # Update memory parameters
            self.memory.lambda_l1 = float(memory_state["lambda_l1"])
            self.memory.lambda_l2 = float(memory_state["lambda_l2"])
            self.memory.lambda_l3 = float(memory_state["lambda_l3"])
            self.memory.theta_l1 = float(memory_state["theta_l1"])
            self.memory.theta_l2 = float(memory_state["theta_l2"])
            self.memory.gating12 = float(memory_state["gating12"])
            self.memory.gating23 = float(memory_state["gating23"])

            # Restore memory levels
            self.memory.l1[:] = new_l1
            self.memory.l2[:] = new_l2
            self.memory.l3[:] = new_l3

            # Restore QILM state
            new_qilm_memory = [
                np.array(vec, dtype=float) for vec in qilm_state["memory"]
            ]
            new_qilm_phases = list(qilm_state["phases"])

            self.qilm.memory = new_qilm_memory
            self.qilm.phases = new_qilm_phases

            logger.info(
                "Loaded system state from %s (format_version=%d, "
                "memory_dim=%d, qilm_entries=%d)",
                filepath,
                file_version,
                self.dimension,
                len(self.qilm.memory),
            )

        except Exception as e:
            # This should not happen if validation is correct, but log it
            logger.error(
                "Failed to restore state from %s after validation: %s",
                filepath,
                e,
            )
            raise StateCorruptError(
                filepath=filepath,
                reason=f"Failed to restore state: {e}",
            ) from e
