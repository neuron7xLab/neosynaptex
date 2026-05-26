# Machine Thinking Operational Spec (Algorithmic Form)

## Scope
This spec translates conceptual language into executable mechanisms.

## Pipeline
1. **Validate** checklist (`validate_thinking_checklist.py`) -> report `R`.
2. **Render** product artifact (`generate_thinking_product_report.py`) -> JSON+MD.
3. **Compile** operational artifact (`compile_thinking_artifact.py`) -> divergence/convergence plan.

## Core Functions

### F1: Completion
\[
completion\_ratio = checked\_items / total\_items
\]

### F2: Weighted Value
\[
value\_score = \frac{\sum_s w_s \cdot checked_s}{\sum_s w_s \cdot total_s}
\]

### F3: Capital Index
\[
capital\_index = 0.5\cdot value\_score + 0.3\cdot completion\_ratio + 0.2\cdot structure\_ok
\]
where `structure_ok ∈ {0,1}`.

### F4: Verdict
- `basic`: PASS iff `total>0 && completion_ratio>=min_completion && capital_index>=min_capital_index`.
- `research_v1`: PASS iff `total>0 && unchecked=0 && structure_ok && capital_index>=min_capital_index`.

### F5: Divergence
For each unresolved section `s` with count `u_s` and actions `A_s`, emit tasks:
\[
priority(task_{s,i}) = w_s \cdot u_s
\]
Sort by descending priority.

### F6: Convergence
Return first `top_k` tasks as minimal action vector.

### F7: Counterfactuals
For each converged action `a`, emit falsifier:
- Hypothesis: skipping `a` degrades quality.
- Test: run without `a` and compare `Δ capital_index`.

## Contracts
- Report schema: `mt-report/v1`.
- Operational artifact schema: `mt-operational-artifact/v1`.
- Compiler input keys required: `verdict`, `capital_index`, `unresolved_by_section`, `action_plan`.

## Determinism Rules
- UTC timestamps only.
- Stable sorting keys: `(-priority, section, task_id)`.
- Fail-closed on malformed contract.


## Convergence status contract
- `ACTION_REQUIRED`: at least one prioritized task exists.
- `NO_ACTION_REQUIRED`: unresolved set is empty; operational vector is intentionally empty.
