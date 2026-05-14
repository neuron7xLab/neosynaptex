# EAI Graded Falsification Phase Diagram v1 — Report

> Companion to
> [`EAI_GRADED_FALSIFICATION_PHASE_DIAGRAM_V1.md`](EAI_GRADED_FALSIFICATION_PHASE_DIAGRAM_V1.md)
> (pre-registration). Records the verdict on the first run and the
> regions discovered.

## A. What changed

- New library `core/eai/graded_phase_diagram.py` — pure deterministic
  functions over the 6-axis grid.
- New runner `tools/eai/run_graded_falsification_phase_diagram.py` —
  emits JSON + CSV + Markdown deterministically.
- New tests `tests/eai/falsification/test_graded_phase_diagram.py` —
  15 invariant tests.
- New CI workflow `.github/workflows/eai-graded-phase-diagram.yml` —
  determinism replay + anchor preservation + production-engine-
  untouched invariant.
- New artifacts (sha-pinned):
  - `artifacts/eai/phase_diagrams/graded_falsification_phase_diagram_v1.json`
  - `artifacts/eai/phase_diagrams/graded_falsification_phase_diagram_v1.csv`
  - `artifacts/eai/phase_diagrams/graded_falsification_phase_diagram_summary.md`

## B. What did not change

- `core/eai/engine.py` — production engine, untouched.
- `core/iev_gate.py` — production IEV gate, untouched.
- `core/falsification_engine.py` — no edits beyond what shipped in #195.
- `core/eai/graded_gate.py` — no edits beyond what shipped in #195.
- `data/eai_calibration/false_promotion_benchmark_v1.jsonl` — untouched.
- `data/eai_calibration/false_promotion_benchmark_v1_1.jsonl` — untouched.
- `artifacts/eai/benchmarks/falsifiability_test_v1_report.json`
  (PR #195 anchor) — UNTOUCHED, verdict still NULL_RESULT.
- `tests/eai/calibration/test_falsifiability_v1.py` — UNTOUCHED.

## C. Why PR #195 NULL_RESULT remains valid

PR #195 ran the binary vs graded comparison on a **single dataset**
(`false_promotion_benchmark_v1_1.jsonl`, 150 rows) at a **single
operating point** (available_paths=2, fixed substrate text templates,
real-match falsifiers only). That single-point experiment returned
NULL_RESULT honestly.

This PR's phase diagram **does not contradict that finding**. It
extends the search to a 20736-cell grid and looks for *separable
regions* of input space where the gates diverge. The 150-row v1_1
dataset corresponds to a small subset of this grid (specifically:
`evidence_path_count = 2`, `boundary_state = valid`,
`revalidation_state` depends on row, `claim_class ∈ {true_bounded,
false_*, ambiguous, adversarial_*}`). Inside that subset, the v1
verdict NULL_RESULT remains the correct call.

The phase diagram exposes what the single-point experiment could
not: the **rest** of the input space.

## D. Phase regions found

| metric | value |
|---|---:|
| total cells | 20736 |
| useful cells (graded helps without false-killing) | 117 |
| regression cells (graded kills true evidence) | 648 |
| null cells (graded equals binary) | 19971 |
| true_bounded regression cells | 648 |
| **VERDICT** | **REGRESSION_REGION_FOUND** |
| verdict_reason | useful_cells_global=117 AND true_bounded.regression_cells=648 |

## E. Regions where graded helps

Per-class `graded_delta_false_promotion`:

| claim_class | binary FPR | graded FPR | ΔFPR | useful cells |
|---|---:|---:|---:|---:|
| `false_subtle` | 0.3333 | 0.3009 | **−0.032** | 84 |
| `ambiguous` | 0.3333 | 0.3206 | **−0.013** | 33 |

These are the ONLY two classes where graded falsification reduces
false promotion vs binary. The improvements exist exclusively in
sub-regions of high `conflict_marker_count` + `high`
`contradiction_density` combined with low `evidence_path_count`
(consistent with the pre-registered hypothesis).

## F. Regions where graded harms

**`true_bounded` regression: 648 cells (25% of class) killed by
graded gate.** These are cells where:

- `boundary_state ∈ {valid, expanded}` (so `can_be_promoted` passes
  binary), AND
- `revalidation_state = passed`, AND
- `conflict_marker_count >= 1`, AND
- `contradiction_density ∈ {low, medium, high}` (≥1 noise marker
  shares 2+ tokens with the bounded-claim text), AND
- `evidence_path_count < required_paths(conflict_strength)`.

The graded threshold collateral-damages true evidence by raising
the required-paths bar past the available-paths supply when noise
markers incidentally match enough tokens. This is the price of
graded sensitivity.

## G. Regions where graded equals binary

19971 cells (96.3% of grid) — graded verdict = binary verdict.
Dominant cases:
- `conflict_marker_count = 0` (no markers, nothing to grade)
- `boundary_state ∈ {missing, contradictory}` (already fail-closed)
- `false_obvious` and adversarial-* classes with full-substring
  hits (binary already catches them; graded adds nothing)

## H. Is v2 hypothesis worth testing?

**Conditional yes, with operator authorization and fresh
pre-registration**. The phase diagram identifies a non-empty useful
region (117 cells across `false_subtle` + `ambiguous`) — graded
does have signal. But the cost is 648 true-bounded regression
cells under the current constants. A v2 hypothesis worth testing:

> Can the graded threshold be tightened (e.g. require a hit-confirmation
> step or a noise-filter on token-overlap markers) so that the useful
> region is preserved while the true_bounded regression region
> collapses to zero?

This is a SEPARATE PR with SEPARATE pre-registration. It is NOT
part of this PR.

## I. Next legal PR options (after this PR merges)

1. **Dataset v2**: a real-call dataset (not synthetic templates)
   where noise-marker density on bounded claims is empirically
   measured rather than synthetically dialled.
2. **Constants v2**: tightened token-overlap weight (e.g. require
   matched tokens to be domain-specific, not stopword-class) — fresh
   pre-registration mandatory.
3. **Abandon graded gate**: the phase diagram shows graded only
   helps by collateral damage; archive as documented negative
   finding; remove the graded_gate module from public surface
   (keep in private diagnostic tooling).
4. **Keep as diagnostic-only**: do not promote, but retain as a
   measurement tool for future inputs.

## J. CC-META-001 status

- **Gate A (pre-registration)**: PASS — verdict rules + axes + ranges
  declared in `EAI_GRADED_FALSIFICATION_PHASE_DIAGRAM_V1.md` BEFORE
  this run.
- **Gate D (forbidden claims)**: PASS — no forbidden phrasings
  emitted; semantic-drift gate to verify.
- **Gate G (final CI)**: pending merge.
- **Claim tier**: FALSIFIED for the narrow claim "graded gate, at
  these constants, produces a separable useful region without
  collateral damage on true evidence." The infrastructure ships
  as TENTATIVE diagnostic tooling.

## Claim boundary

> EAI Graded Falsification Phase Diagram v1 maps the behavioural
> difference between binary and graded gates over a deterministic
> 6-axis synthetic grid (20736 cells). It identifies, classifies,
> and reports useful / regression / null regions. No production
> engine has been modified. No claim about substrate behaviour,
> brain mechanism, or AGI is asserted.

**Operator law (verbatim from task order)**:
> If the result is ugly, preserve it. If graded gate is useless,
> say so. If it only works by killing true evidence, call it
> regression. No rescue tuning. No pretty lie.

We did. The result is `REGRESSION_REGION_FOUND`. It is preserved.

---

**Run timestamp**: 2026-05-14
**Branch**: `eai/graded-falsification-phase-diagram-v1`
**Anchor preservation**: PR #195 NULL_RESULT untouched (CI-enforced)
**Production engine**: untouched (CI-enforced)
