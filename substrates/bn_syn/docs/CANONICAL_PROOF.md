# Canonical Emergence Proof Path

`README.md` is the single canonical entry surface for users.
This document is the reference specification for the canonical proof command and artifact contract.

`bnsyn run --profile canonical --plot --export-proof` is the canonical command for a single reproducible BN-Syn emergence proof run.

## Command

```bash
bnsyn run --profile canonical --plot --export-proof
```

Optional controls:

```bash
bnsyn run --profile canonical --plot --export-proof --output artifacts/canonical_run
```

## Artifact contract (required)

Canonical base bundle (`bnsyn run --profile canonical --plot`):

- `emergence_plot.png` — primary canonical emergence visual, a composite image built from spike raster activity and population rate dynamics.
- `summary_metrics.json` — numeric summary for the run.
- `run_manifest.json` — reproducibility manifest including command metadata and artifact hashes for external artifacts; self-entry stores a deterministic self-hash computed from canonical manifest JSON with the self-entry normalized to a fixed placeholder token.
- `criticality_report.json` — machine-readable criticality metrics derived from the canonical run traces.
- `avalanche_report.json` — machine-readable avalanche event-structure metrics from contiguous nonzero spike-count bins.
- `phase_space_report.json` — machine-readable state-space trajectory metrics from population rate, sigma, and coherence traces.
- `population_rate_trace.npy` — deterministic raw population-rate trace used for phase-space evidence.
- `sigma_trace.npy` — deterministic raw sigma trace used for phase-space evidence.
- `coherence_trace.npy` — deterministic raw coherence trace used for phase-space evidence.
- `phase_space_rate_sigma.png` — deterministic phase-space trajectory rendering in `(rate, sigma)`.
- `phase_space_rate_coherence.png` — deterministic phase-space trajectory rendering in `(rate, coherence)`.
- `phase_space_activity_map.png` — deterministic `(rate, sigma)` occupancy/density activity map.
- `avalanche_fit_report.json` — deterministic avalanche fit evidence with machine-readable validity verdict.
- `robustness_report.json` — fixed 10-seed reproducibility/admissibility run table + same-seed replay trace-hash evidence.
- `envelope_report.json` — admissibility-band validation summary for the fixed 10-seed run set.

Export-proof augmented bundle (`bnsyn run --profile canonical --plot --export-proof`):

- all base bundle artifacts, plus
- `proof_report.json` — gate-evaluated proof verdict evaluated against the finalized `run_manifest.json` state.
- `product_summary.json` — machine-readable human-surface summary emitted for local reviewer convenience.
- `index.html` — primary human-readable review surface emitted alongside the proof bundle.

## Human-first inspection rule

The primary human interface is `artifacts/canonical_run/index.html`.
Open that report first, then follow the ordered artifact inspection sequence defined in [README.md](../README.md).
For the full product-surface contract check after a canonical export-proof run, execute `bnsyn validate-bundle artifacts/canonical_run`.

## Mechanism narrative (research-facing)

BN-Syn models a recurrent spiking network where:

- **AdEx neuron dynamics** provide biologically motivated membrane and adaptation behavior.
- **STDP synapses** implement timing-dependent weight updates; memory/consolidation modules build on these weight dynamics.
- **Criticality control** tracks branching/sigma behavior and adjusts global excitability.

The canonical proof path is intentionally one-run and one-command so external reviewers can inspect concrete behavior without repository archaeology.

## Reproducibility

Reproducibility is enforced through explicit seed, deterministic simulation path, manifest hashing, and a fixed 10-seed admissibility-band check.
Use `run_manifest.json` + `criticality_report.json` + `avalanche_report.json` + `phase_space_report.json` + `summary_metrics.json` to compare repeated runs under same parameters.

## Interpretation layer and limits

- **Directly measured signals:** spike events per step, sigma, active-fraction coherence, spike rate.
- **Derived metrics:** means/peaks and event counts in `summary_metrics.json`.
- **Interpretation layer:** evidence of emergent network dynamics under this model implementation and parameterization.
- **Out of scope / unsupported claims:** cognition, consciousness, AGI/ASI capability, or biological equivalence claims not directly validated by repository experiments.
