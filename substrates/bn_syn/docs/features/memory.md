# Memory Trace Operational Notes

## Scope
This page documents runtime invariants for `bnsyn.memory.MemoryTrace` and `MemoryConsolidator` that are required for safe production execution.

## Runtime invariants
- `capacity` must be positive.
- Seeded `patterns`, `importance`, `timestamps`, and `recall_counters` must have matching lengths.
- `tag()` stores a detached `float64` copy of each pattern.
- `remove_at(idx)` keeps metadata arrays aligned with pattern order.
- `get_state()` returns copies of arrays and can be safely mutated by callers.

## Validation gates
- Unit tests in `tests/test_memory_trace_unit.py` cover initialization guards, removal branches, and dtype/copy safety checks.
- Integration behavior is exercised by memory and consolidator suites in `tests/test_memory.py` and `tests/test_memory_consolidator.py`.
