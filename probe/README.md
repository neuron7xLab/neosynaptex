# neosynaptex-probe — Dialogue Substrate Adapter

**Experimental** substrate for the neosynaptex gamma engine family. Probes
human–AI conversation sessions as a candidate edge-of-chaos substrate,
subject to a four-test anti-tautology battery (AT-1..AT-4) and a
three-test falsification battery against an explicit null-result contract.

`DialogueAdapter.domain == "dialogue"`. `topo` = cumulative vocabulary
size; `thermo_cost` = cumulative token count. Gamma is computed via the
canonical neosynaptex engine (`core.gamma.compute_gamma`, Theil-Sen +
bootstrap CI) and **never stored inside probe**.

---

## CLAIM BOUNDARY

> **This probe does not measure consciousness, intelligence, or truth.**
> It measures one thing: the empirical scaling exponent γ in the power
> law `thermo_cost ~ topo^(-γ)` across a dialogue session, as
> extracted by the canonical neosynaptex gamma engine. γ close to 1
> indicates the session lives near the scaling point where vocabulary
> breadth grows sub-linearly with conversational depth; γ ≠ 1 does not
> imply malfunction and γ ≈ 1 does not imply criticality-of-thought.
> Any interpretation beyond the literal power-law exponent is the
> reader's, not the instrument's.

This verbatim paragraph also appears in §2 of `preprint/probe_dialogue_preprint.md`.

---

## Repository layout

```
probe/
├── pyproject.toml            # neosynaptex-probe 0.1.0; deps = numpy, scipy
├── README.md                 # this file (claim boundary § verbatim)
├── Dockerfile                # deterministic reproduction container
├── seed_ledger.json          # append-only JSONL seed log (HARD RULE 8)
├── reproduce.py              # SYNTHETIC — engineering only (HARD RULE 6)
├── src/probe/
│   ├── dialogue_adapter.py   # DomainAdapter Protocol implementation
│   ├── session.py            # ProbeSession wrapping nx.observe()
│   ├── anti_tautology.py     # AT-1..AT-4 battery
│   ├── falsification.py      # perm + Cohen's d + KS; null-result contract
│   └── ingestion.py          # JSONL fail-closed validation
├── tests/                    # 45 tests, pytest + mypy strict + ruff clean
├── evidence/
│   ├── engineering/          # reproduce.py outputs (SYNTHETIC)
│   └── scientific/           # real-data outputs (only if AT battery passes)
└── preprint/
    └── probe_dialogue_preprint.md
```

## Quick start

```bash
cd probe
pip install -e ".[dev]"
# Requires parent repo on sys.path for neosynaptex + contracts:
export PYTHONPATH="$(pwd)/src:$(pwd)/.."
pytest tests/ -v            # 45/45 green
mypy --strict src/probe/    # 0 errors
python reproduce.py         # writes evidence/engineering/*.json
```

Docker:

```bash
cd ..   # repo root
docker build -f probe/Dockerfile -t neosynaptex-probe:0.1.0 .
docker run --rm neosynaptex-probe:0.1.0   # runs probe/reproduce.py
```

## HARD RULES (enforced by CI)

1. `probe/` never imports gamma engine directly — only via `nx.observe()`.
2. `DialogueAdapter.topo()` and `.thermo_cost()` never decrease.
3. Gamma never stored on probe objects — read from `NeosynaptexState` only.
4. `run_anti_tautology().passed` must be `True` before any result enters
   `evidence/scientific/`.
5. `null_confirmed` (gamma_llm < 0) is a scientific result, documented
   in `FalsificationResult` — never hidden, never re-labelled as failure.
6. `reproduce.py` output is always labelled `SYNTHETIC — engineering only`.
7. `evidence/engineering/` and `evidence/scientific/` are separate dirs.
8. Seed is logged to `seed_ledger.json` before any stochastic operation.
9. Claim boundary statement appears verbatim in this README and
   `preprint/probe_dialogue_preprint.md` §2.
10. `mypy --strict`: zero errors on every commit.
11. All CONTRACT.md invariants from neosynaptex (YV1, I-1..I-5, power-law)
    continue to hold — probe does not mutate neosynaptex internals.
12. Streamlit is in `[demo]` extras only; core dependencies = `{numpy, scipy}`.

## Scientific contract

Use `probe.ingestion.ingest_jsonl` to admit a real corpus (one
session per line, schema in `ingestion.py`). Rejected sessions are
written to a rejection log — never silently dropped. Promote a gamma
value to `evidence/scientific/` only when:

- `export_evidence()` succeeded (n_turns ≥ MIN_TURNS = 8),
- `run_anti_tautology(session).passed == True`,
- `run_falsification(human_ai, llm)` reports a non-degenerate battery,
- seed is logged to `seed_ledger.json`.

This extends the existing `experiments/lm_substrate/` null result
(gamma = -0.094, p = 0.626 on stateless GPT-4o-mini) with real
human–AI dialogue data. A null result on dialogue is a publishable
outcome and sets `null_confirmed = True`.
