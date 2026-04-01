# Layering Rules — MFN v0.1.0

## Canonical Layer Order (bottom → top)

```
Layer 0: types/           — frozen dataclasses, enums, no logic
Layer 1: numerics/        — grid ops, update rules, pure math
Layer 2: core/            — R-D engine, detect, diagnose, thermodynamic kernel
Layer 3: analytics/       — TDA, entropy, fractals, morphology (READ-ONLY on fields)
Layer 4: bio/, neural/, neurochem/ — domain-specific extensions
Layer 5: intervention/    — planning layer (consumes core + analytics)
Layer 6: interpretability/ — READ-ONLY auditor (consumes core + analytics + types)
Layer 7: self_reading/    — READ-ONLY + recovery.py → {Θ, PID}
Layer 8: tau_control/     — READ-ONLY + transformation.py → {C}
Layer 9: experiments/     — simulation runner, PRR export
Layer 10: pipelines/      — high-level orchestration
Layer 11: integration/    — API, WebSocket, connectors (top-level)
```

## Rules

1. **Lower layers MUST NOT import higher layers.**
   types/ never imports core/. core/ never imports integration/.

2. **READ-ONLY modules (L6-L8) MUST NOT import simulation execution.**
   Forbidden: `from mycelium_fractal_net.core.simulate import ...`
   Allowed: `from mycelium_fractal_net.types.field import FieldSequence`

3. **WRITE access is explicitly bounded:**
   - `self_reading/recovery.py` → {Θ, PID} only
   - `tau_control/transformation.py` → {C} only
   - All other modules in L6-L8 are READ-ONLY

4. **gamma is diagnostic output, never control input.**
   No module in L7-L8 may use gamma as threshold, reward, or objective.

5. **Cross-layer data exchange uses typed contracts from types/.**
   Prefer `FieldSequence`, `MorphologyDescriptor`, `CausalValidationResult`
   over `dict[str, Any]`.

## Enforcement

- `.importlinter`: 10 contracts enforce forbidden imports
- Tests: `test_tau_control.py::test_no_gamma_in_interface`
- Architecture: `docs/architecture/ARCHITECTURE_AUDIT.md`
