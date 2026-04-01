# STATE_SYSTEM: System State Persistence

## Overview

This document describes the persisted system state infrastructure for MLSDM,
including schemas, storage, migrations, and recovery procedures.

## What is Stored

The `SystemStateRecord` contains:

1. **Memory State** (`MemoryStateRecord`): MultiLevelSynapticMemory state
   - `dimension`: Vector dimension (int > 0)
   - `lambda_l1/l2/l3`: Decay rates (float in (0, 1])
   - `theta_l1/l2`: Consolidation thresholds (float > 0)
   - `gating12/23`: Gating factors (float in [0, 1])
   - `state_l1/l2/l3`: Memory level vectors (list of floats). Aliases: `state_L1/L2/L3`

2. **QILM State** (`QILMStateRecord`): Quantum-Inspired Lattice Memory state
   - `memory`: List of memory vectors
   - `phases`: List of phase values (must match memory length)

3. **Metadata**:
   - `version`: Schema version for migrations
   - `id`: Optional unique identifier
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp

## Schema (Pydantic Models)

```python
from mlsdm.state import SystemStateRecord, MemoryStateRecord, QILMStateRecord

# Create memory state
memory = MemoryStateRecord(
    dimension=10,
    lambda_l1=0.5,
    lambda_l2=0.1,
    lambda_l3=0.01,
    theta_l1=1.0,
    theta_l2=2.0,
    gating12=0.5,
    gating23=0.3,
    state_L1=[0.0] * 10,
    state_L2=[0.0] * 10,
    state_L3=[0.0] * 10,
)

# Create QILM state
qilm = QILMStateRecord(memory=[], phases=[])

# Create system state
state = SystemStateRecord(
    version=1,
    memory_state=memory,
    qilm=qilm,
)
```

## Invariants

### MemoryStateRecord
- `dimension > 0`
- `0 < lambda_l1 <= 1`, `0 < lambda_l2 <= 1`, `0 < lambda_l3 <= 1`
- `theta_l1 > 0`, `theta_l2 > 0`
- `0 <= gating12 <= 1`, `0 <= gating23 <= 1`
- `len(state_l1) == len(state_l2) == len(state_l3) == dimension`

### QILMStateRecord
- `len(memory) == len(phases)`

### SystemStateRecord
- `version >= 1`
- `created_at <= updated_at`
- `id` cannot be empty string (if provided)

## Physical Storage

State is stored in JSON or NPZ format:

```python
from mlsdm.state import save_system_state, load_system_state

# Save as JSON (recommended)
save_system_state(state, "/path/to/state.json")

# Save as NPZ (for large states)
save_system_state(state, "/path/to/state.npz")

# Load
state = load_system_state("/path/to/state.json")
```

### File Layout

When saving to `/path/state.json`:
- `/path/state.json` - Main state file
- `/path/state.json.backup` - Backup (created on overwrite)
- `/path/state.json.checksum` - SHA-256 checksum for integrity

## Write Path

All writes go through `save_system_state()`:

```python
from mlsdm.state import save_system_state

save_system_state(
    state,
    filepath,
    create_backup=True,   # Create backup before overwriting
    state_id="my-state",  # Optional unique ID
)
```

Features:
- Atomic writes (temp file + rename)
- Checksum generation for JSON files
- Automatic backup creation on overwrite
- Schema validation before write
- Retry on failure (3 attempts)

## Read Path

All reads go through `load_system_state()`:

```python
from mlsdm.state import load_system_state

state = load_system_state(
    filepath,
    verify_checksum=True,   # Verify integrity on load
    auto_migrate=True,      # Auto-migrate old versions
)
```

Features:
- Checksum verification (optional)
- Automatic schema migration
- Schema validation on load
- Integrity warnings for anomalies

## Migrations

### Schema Versions

- **v0** (legacy): `{"memory_state": {...}, "qilm": {...}}`
- **v1** (current): Adds `version`, `id`, `created_at`, `updated_at`

### Adding Migrations

```python
from mlsdm.state.system_state_migrations import register_migration

def migrate_v1_to_v2(state: dict) -> dict:
    # Transform state from v1 to v2 format
    state["new_field"] = "default_value"
    return state

register_migration(1, 2, migrate_v1_to_v2)
```

## Recovery Procedures

### Automatic Recovery

```python
from mlsdm.state import recover_system_state

try:
    state = recover_system_state("/path/to/state.json")
except StateRecoveryError:
    # Manual intervention required
    pass
```

Recovery process:
1. Try loading main file
2. If corrupted, try backup file
3. Restore backup to main file
4. If both fail, raise `StateRecoveryError`

### Manual Recovery

If automatic recovery fails:

1. Check backup file exists: `state.json.backup`
2. Verify backup integrity manually
3. Copy backup over main file
4. Delete corrupted checksum file
5. Load with `verify_checksum=False`

## Usage with MemoryManager

The state module integrates with `MemoryManager`:

```python
from mlsdm.state import (
    SystemStateRecord,
    save_system_state,
    load_system_state,
    create_empty_system_state,
)

# Create empty state
state = create_empty_system_state(dimension=384)

# Save after processing
save_system_state(state, "memory_state.json")

# Load on restart
state = load_system_state("memory_state.json")
```

## Error Handling

```python
from mlsdm.state.system_state_store import (
    StateLoadError,      # Load failed
    StateSaveError,      # Save failed
    StateCorruptionError, # Checksum mismatch
    StateRecoveryError,  # Recovery failed
)

try:
    state = load_system_state("state.json")
except StateCorruptionError:
    state = recover_system_state("state.json")
except StateLoadError:
    state = create_empty_system_state()
```

## Testing

Run tests with:

```bash
pytest tests/state/test_system_state_integrity.py -v
```

## See Also

- [ARCHITECTURE_SPEC.md](../ARCHITECTURE_SPEC.md) - Overall architecture
- [src/mlsdm/state/](../src/mlsdm/state/) - Source code
- [src/mlsdm/memory/](../src/mlsdm/memory/) - Memory subsystem
