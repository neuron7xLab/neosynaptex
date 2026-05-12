# Regime Controller Engineering Guide (handover-ready)

## 1. Purpose
`bnsyn.regime` is a control-loop component for online adaptation:
1) estimate `gamma` from activations,
2) compute internal action/rest gate,
3) apply adaptive update and optional rest consolidation,
4) emit auditable diagnostics and optional JSONL ledger record.

## 2. What is tested vs hypothesized
- **TESTED:** numerical behavior and contracts of `compute_gamma`, gating, update, diagnostics, ledger format.
- **HYPOTHESIS:** biological/cognitive interpretation of gamma as regime marker.

## 3. Runtime flow
```mermaid
flowchart LR
A[activations] --> B[compute_gamma]
B --> C{finite gamma?}
C -- yes --> D[gate(gamma, entropy)]
C -- no --> E[gamma_target fallback + flag]
E --> D
D --> F[adaptive_update]
F --> G[diagnostics]
G --> H[optional JSONL ledger]
```

## 4. Operational contracts
- Input shape: `weights.shape == grad.shape`.
- `learning_rate >= 0`.
- Gate output must remain in `[0,1]`.
- Diagnostics entropy is clipped to `[0,1]`.
- Fallback events are explicit: `gamma_fallback_used=True`.
- Ledger timestamp must be UTC (`...Z`).

## 5. Files map (for new engineer)
- Logic: `src/bnsyn/regime.py`
- Invariants: `invariants.yaml`
- Formal spec: `docs/specs/regime_controller_spec.md`
- Release gate: `scripts/check_regime_release_gate.py`
- CI gate: `.github/workflows/bn-syn-regime-gate.yml`
- Tests:
  - unit: `tests/test_regime.py`
  - invariants: `tests/test_invariants_contract.py`
  - property: `tests/property/test_regime_properties.py`
  - golden: `tests/golden/test_regime_golden.py`
  - validation: `tests/validation/test_gamma_proxy_synthetic.py`
  - ledger: `tests/test_regime_ledger.py`
  - governance: `tests/test_governance_roles.py`

## 6. One-command verification
```bash
python scripts/check_regime_release_gate.py
```

## 7. Failure triage
1. Run gate command.
2. If invariant failure -> fix `invariants.yaml` / test bindings.
3. If golden drift -> check intentional logic change; update fixture with changelog note.
4. If ledger failure -> verify UTC suffix and schema fields.
5. If governance failure -> check role uniqueness constraints.

## 8. Rollback and kill-switch
- Kill-switch: set `learning_rate=0` or bypass controller.
- Rollback: `git revert <regime-related-commit>`.

## 9. Minimal integration snippet
```python
controller = RegimeController(learning_rate=1e-3)
weights2, diag = controller.step(weights, grad, activations, entropy)
record = build_run_record(weights, weights2, diag, {"lr": 1e-3})
append_run_record_jsonl("regime_ledger.jsonl", record)
```
