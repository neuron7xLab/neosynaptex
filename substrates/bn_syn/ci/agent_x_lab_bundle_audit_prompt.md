# Agent-X-Lab Canonical Bundle Audit Prompt (RCT FSM v2)

Use this finite-state prompt in Agent-X-Lab pipelines to audit canonical BN-Syn bundles deterministically.

## Reasoning Contract (FSM)

### [INIT]
**Entry conditions**
- Input contains `<ARTIFACT_DIR>`.
- Auditor has shell access only.

**Actions**
- Initialize result object with `status=FAIL` (fail-closed default).
- Register required files:
  - `run_manifest.json`
  - `summary_metrics.json`
  - `proof_report.json`
  - `product_summary.json`
  - `index.html`

**Transitions**
- If `<ARTIFACT_DIR>` missing/unreadable -> `[EMIT]` with reason `artifact_dir_unreadable`.
- Else -> `[GATHER]`.

---

### [GATHER]
**Actions**
1. Run command:
   - `bnsyn validate-bundle <ARTIFACT_DIR>`
2. Capture:
   - exit code
   - stdout
   - stderr
3. Check required file existence list.
4. Load JSON files (`product_summary.json`, `proof_report.json`) if present.

**Transitions**
- On any command execution error -> `[EMIT]` with reason `command_execution_error`.
- Else -> `[VERIFY]`.

---

### [VERIFY]
**Checks**
- Required files all exist.
- `product_summary.proof_verdict == proof_report.verdict`.
- `product_summary.status == product_summary.proof_verdict`.
- Command exit code indicates pass semantics (`0`) when no failures detected.

**Policy**
- Missing file -> fail with `missing artifact: <name>`.
- JSON parse failure -> fail with `json_parse_error: <name>`.
- Never infer absent evidence.

**Transitions**
- If any check fails -> `[EMIT]` with accumulated reasons.
- If all checks pass -> `[EMIT]` with `status=PASS`.

---

### [EMIT]
Emit strict JSON:
```json
{
  "status": "PASS|FAIL",
  "reasons": ["..."],
  "evidence": {
    "command": "bnsyn validate-bundle <ARTIFACT_DIR>",
    "exit_code": 0,
    "stdout_excerpt": "...",
    "stderr_excerpt": "..."
  }
}
```

## Safety Invariants
- Fail-closed baseline in `[INIT]`.
- PASS is impossible without command evidence from `[GATHER]`.
- All transitions are explicit; no hidden states.
