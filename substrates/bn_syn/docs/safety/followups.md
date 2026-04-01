# Safety Follow-ups

## FUP-001: Deterministic thread/BLAS controls

**Hazard**: H4  
**Owner**: Safety Engineering  
**Status**: Planned  
**Action**: Add explicit environment controls for thread/BLAS determinism (e.g., `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`) in runtime entrypoints and CI, with validation tests ensuring reproducibility under fixed settings.  
**Target evidence**: Determinism tests running with explicit thread controls in CI.

## FUP-002: Runtime numeric health checks

**Hazard**: H5  
**Owner**: Safety Engineering  
**Status**: Planned  
**Action**: Integrate `validate_numeric_health` checks into runtime state updates (`Network.step`/`step_adaptive`) and add regression tests verifying fail-closed behavior on NaN/Inf injections.  
**Target evidence**: New tests in `tests/validation` and explicit runtime checks in `src/bnsyn/sim/network.py`.
