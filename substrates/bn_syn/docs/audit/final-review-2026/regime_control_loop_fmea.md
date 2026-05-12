# FMEA: Regime Control Loop

| Failure mode | Effect | Detection | Mitigation |
|---|---|---|---|
| Non-finite gradients | NaN/Inf weights | adaptive_update finite checks | ValueError fail-closed + grad clipping |
| Short activations | invalid gamma estimate | gamma_fallback_used flag | fallback to gamma_target with explicit diagnostics |
| High entropy bursts | unstable action decisions | gate bounded tests | entropy threshold => rest bias |
| Ledger write error | audit gap | RuntimeError + structured error log | fail-fast, operator retry |
| Governance config drift | unclear authority | governance tests | uniqueness and count validation |
