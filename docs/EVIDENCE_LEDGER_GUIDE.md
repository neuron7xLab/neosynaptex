# Evidence Ledger Guide

> **Audience:** contributors, reviewers, and auditors who need to understand
> the structure and semantics of the NeoSynaptex evidence system.
>
> The evidence system consists of `evidence/gamma_ledger.json`, the
> `evl/` proof chain directory, and `CANONICAL_OWNERSHIP.yaml`. Together
> they form a tamper-evident, append-only record of all validated gamma
> measurements.

---

## Overview

```
evidence/
  gamma_ledger.json          # authoritative gamma values per substrate
  gamma_provenance.md        # tier classification and falsification conditions
  data_hashes.json           # SHA-256 hashes of all T1 data files
  PREREG.md                  # pre-registration commit hashes

evl/                         # structured proof chain entries (JSONL)
  proof_chain.jsonl          # append-only proof chain

CANONICAL_OWNERSHIP.yaml     # authorship and provenance declaration
```

---

## `gamma_ledger.json` — Schema

The ledger is a JSON object with two top-level keys:

```json
{
  "version": "1.0.0",
  "invariant": "gamma derived only, never assigned",
  "entries": {
    "<substrate_key>": { ... }
  }
}
```

### Entry schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `substrate` | `string` | yes | Internal substrate identifier (matches adapter `domain`) |
| `description` | `string` | yes | Human-readable description of what this substrate measures |
| `gamma` | `number` | yes | Theil-Sen gamma exponent (point estimate) |
| `ci_low` | `number` | yes | Bootstrap 95% CI lower bound |
| `ci_high` | `number` | yes | Bootstrap 95% CI upper bound |
| `r2` | `number \| null` | yes | R² of log-log fit. `null` if not computed for this entry. |
| `n_pairs` | `integer \| null` | yes | Number of (topo, cost) pairs used. `null` if not tracked. |
| `p_permutation` | `number \| null` | yes | Permutation p-value. `null` if not computed. |
| `status` | `string` | yes | One of: `VALIDATED`, `PENDING`, `DERIVED`, `CONSTRUCTED` |
| `tier` | `string` | yes | Evidence tier: `evidential`, `simulation`, `exploratory`, `excluded` |
| `locked` | `boolean` | yes | If `true`, the entry is frozen (values may not be changed) |
| `data_source` | `object` | yes | `{file: string\|null, sha256: string\|null}` |
| `adapter_code_hash` | `string \| null` | yes | SHA-256 of the adapter file at measurement time |
| `derivation_method` | `string` | yes | Human-readable description of how gamma was derived |
| `method_tier` | `string` | yes | Method tier: `T1`..`T5` |

### Example entry

```json
"zebrafish_wt": {
  "substrate": "zebrafish",
  "description": "Wild-type zebrafish calcium imaging — topological complexity vs thermodynamic cost",
  "gamma": 1.055,
  "ci_low": 0.89,
  "ci_high": 1.21,
  "r2": 0.76,
  "n_pairs": null,
  "p_permutation": null,
  "status": "VALIDATED",
  "tier": "evidential",
  "locked": true,
  "data_source": {
    "file": "data/zebrafish/Out_WT_default_1.mat",
    "sha256": null
  },
  "adapter_code_hash": null,
  "derivation_method": "McGuirl 2020, derived density->NN_CV",
  "method_tier": "T2"
}
```

---

## Status Values

### `VALIDATED`

The entry has been independently verified. Criteria:
- Bootstrap 95% CI contains 1.0 (or is explicitly documented as out-of-regime).
- R2 >= 0.3 (or documented with explanation if below threshold).
- At least one passing CI test in `tests/`.
- `canonical_gate` passes with this entry present.
- `locked: true` is set — the gamma value is frozen.

**Meaning:** This result is part of the published evidence record. Changes
require creating a new entry (the old entry is kept with a `superseded_by`
note, not deleted — see append-only rule below).

### `PENDING`

The measurement has been made and recorded, but has not yet passed full
validation. The entry exists as a candidate.

When to set `PENDING`:
- Adapter written and tested locally.
- Gamma computed but CI not yet verified.
- Awaiting independent replication.
- Data source not yet fully documented.

**Meaning:** Do not count this substrate in the headline claim count. It
is a work-in-progress.

### `DERIVED`

The gamma value was not measured directly from the substrate but derived
analytically or from a transformation of another measurement.

Example: a theoretical prediction from a mean-field model, or a gamma value
extrapolated from published literature statistics rather than raw data.

**Meaning:** Useful for comparison but not counted as an independent empirical
witness. Must include full derivation in `derivation_method`.

### `CONSTRUCTED`

The substrate was synthetically constructed specifically to test the
methodology — not from natural or empirical data.

Example: a mathematical signal constructed to have exactly gamma = 1.0 by
construction (unit test fixture). Negative controls (white noise, random walk)
also use this status.

**Meaning:** Never counts as evidence for the gamma = 1.0 claim. Used only
for methodology validation and falsification controls.

---

## Evidence Tiers

| Tier | Name | Description |
|------|------|-------------|
| `T1` | Evidential | Real external data from published datasets. Strongest evidence. |
| `T2` | Validated simulation | Simulation validated against real data. |
| `T3` | Simulation | Simulation from first principles. |
| `T4` | Exploratory | Internal system measurements (e.g., cns_ai_loop). Not counted in headline. |
| `T5` | Exploratory + wide CI | Exploratory with wide bootstrap CI. Not primary evidence. |

---

## Proof Chain (`evl/proof_chain.jsonl`)

The proof chain is an append-only JSONL file. Each line is a JSON object
representing one proof bundle entry.

### Reading the proof chain

```python
import json

with open("evl/proof_chain.jsonl") as f:
    entries = [json.loads(line) for line in f if line.strip()]

for entry in entries:
    print(entry["t"], entry["phase"], entry["gamma"]["mean"])
```

### Chain entry schema

Each entry includes the fields from `export_proof()` plus:

| Field | Description |
|-------|-------------|
| `chain.t` | Sequential proof count |
| `chain.prev_hash` | SHA-256 of the previous entry (or `"GENESIS"` for first) |
| `chain.chain_root` | Genesis hash from `evidence_bundle_v1/manifest.json` |
| `chain.self_hash` | SHA-256 of this entry (excluding `self_hash`) |

### Verifying chain integrity

```python
import hashlib, json

with open("evl/proof_chain.jsonl") as f:
    entries = [json.loads(line) for line in f if line.strip()]

prev_hash = "GENESIS"
for i, entry in enumerate(entries):
    # Recompute self_hash
    clean = {k: v for k, v in entry.items() if k != "chain"}
    chain_clean = {k: v for k, v in entry["chain"].items() if k != "self_hash"}
    clean["chain"] = chain_clean
    canonical = json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str)
    computed = hashlib.sha256(canonical.encode()).hexdigest()

    assert computed == entry["chain"]["self_hash"], f"Entry {i}: hash mismatch"
    assert entry["chain"]["prev_hash"] == prev_hash, f"Entry {i}: chain broken"
    prev_hash = entry["chain"]["self_hash"]

print(f"Chain integrity OK ({len(entries)} entries)")
```

---

## `CANONICAL_OWNERSHIP.yaml`

This file declares authorship and provenance for the repository. Fields:

| Field | Description |
|-------|-------------|
| `author` | Primary author (name, contact) |
| `institution` | Affiliation (or "Independent researcher") |
| `license` | Repository license |
| `canonical_url` | GitHub URL |
| `zenodo_doi` | Zenodo archive DOI (set at submission) |
| `substrate_owners` | Per-substrate authorship if different from primary |
| `data_sources` | External dataset attributions |

This file is the authoritative record for IP and attribution. It is used by
`scripts/ci_canonical_gate.py` to verify provenance consistency.

---

## Append-Only Rule

**The evidence ledger is append-only.** Once an entry has `locked: true`,
its `gamma`, `ci_low`, `ci_high`, and `status` fields must not be modified.

If a measurement needs to be corrected:

1. Set the old entry's status to `"SUPERSEDED"` and add a `superseded_by` field.
2. Create a new entry with the corrected values and status `"PENDING"`.
3. After validation, set the new entry to `"VALIDATED"` and `locked: true`.
4. The old entry remains in the ledger (never deleted).

This rule ensures that the pre-registration timestamps in `evidence/PREREG.md`
remain meaningful — you can always recover the exact ledger state at any
point in history via `git log`.

---

## Adding a New Ledger Entry

1. Write the adapter and validate locally (`pytest tests/test_my_substrate.py`).
2. Run `python scripts/ci_canonical_gate.py` — it will report which gate
   requires the new entry.
3. Add the entry to `evidence/gamma_ledger.json` with `status: "PENDING"` and
   `locked: false`.
4. Open a PR. The CI canonical gate will verify the entry structure.
5. After review and CI pass, set `status: "VALIDATED"` and `locked: true`
   in the same PR.
6. The merged commit hash is recorded in `evidence/PREREG.md` as the
   pre-registration timestamp.
