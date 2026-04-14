# PhysioNet NSR2DB HRV Multifractal Pilot — v1.0

> **Substrate.** `physiological_cardiac` (5-subject pilot).
> **Closes two methodology gaps from the n=1 pilot:**
> (1) MFDFA → multifractal width Δh; (2) beat-interval null →
> destroys beat-to-beat order while preserving marginal (closes
> the IAAFT gap).
> **Date.** 2026-04-14.

## 1. TL;DR — n=1 pilot was misleading

**γ varies enormously across 5 subjects (0.07 to 1.09).** The n=1 pilot
on nsr001 was an outlier on the high side. Mean γ ≈ 0.50, std ≈ 0.44 —
no clean cross-subject γ ≈ 1 finding.

**Δh > 0 on all subjects** → cardiac HRV at VLF is **multifractal**, not
monofractal. Multiple co-existing scaling regimes.

**Beat-interval null rejects on 4/5 subjects** → the γ value (whatever
it is per subject) DOES require temporally-ordered beat structure.
Closes the IAAFT gap from the n=1 pilot.

## 2. Per-subject results

| Record | γ | r² | Δh | h(q=2) | beat-null sep? |
|---|---|---|---|---|---|
| nsr001 | 1.0855 | 0.973 | 0.1274 | 1.1826 | **YES** |
| nsr002 | 0.3306 | 0.588 | 0.2382 | 1.0312 | **YES** |
| nsr003 | 0.0724 | -0.070 | 0.2063 | 0.9713 | NO |
| nsr004 | 0.8509 | 0.932 | 0.0611 | 1.1501 | **YES** |
| nsr005 | 0.1687 | 0.920 | 0.2940 | 1.1425 | **YES** |

| | mean | std | range |
|---|---|---|---|
| **γ (Welch VLF)** | **0.5016** | **0.4436** | [0.07, 1.09] |
| **r²** | 0.6687 | — | [-0.07, 0.97] |
| **Δh (MFDFA)** | **0.1854** | 0.0920 | [0.06, 0.29] |
| **h(q=2)** | **1.0955** | 0.0899 | [0.97, 1.18] |

## 3. What changed vs the n=1 pilot

The n=1 pilot reported γ = 1.09, r² = 0.97 on nsr001 with the
interpretation: "γ ≈ 1 with clean fit, 2/3 nulls reject". The
5-subject pilot now shows:

| Aspect | n=1 (nsr001 only) | n=5 |
|---|---|---|
| Headline γ | 1.09 | 0.50 ± 0.44 |
| Cross-subject γ ≈ 1? | "yes" | **no** — wide variability |
| r² consistency | 0.97 | varies 0.07–0.97 |
| New: Δh | not measured | 0.185 ± 0.092 (multifractal) |
| New: beat-interval null | not run | rejects on 4/5 |
| Implication for γ ≈ 1 universal | "supports" | **does not support** |

## 4. What MFDFA Δh tells us

- **All 5 subjects have Δh > 0** → HRV at VLF is multifractal.
- **Δh range 0.06 to 0.29** → moderate multifractality. Not extreme
  (which would be Δh > 0.5–1.0).
- nsr004 has the narrowest Δh (0.06) → closest to monofractal.
- nsr005 has the widest Δh (0.29) → richest multi-regime dynamics.

Per the standard HRV literature interpretation:
- Δh ≈ 0: single scaling exponent, simple monofractal (e.g., Brownian
  noise, fractional Gaussian noise).
- Δh > 0.1: meaningful multifractality, suggests multiple co-existing
  scaling regimes — typical for healthy HRV (Ivanov et al. 1999;
  Goldberger 2002).

The mean Δh ≈ 0.19 is consistent with the published "healthy adult
HRV is multifractal" finding. This is **independent confirmation**
that the substrate has rich dynamics, not just 1/f scaling alone.

## 5. What the beat-interval null tells us

- **4 of 5 subjects: beat-interval null rejects** → γ requires
  temporally-ordered beat-to-beat structure.
- **nsr003 fails** — but nsr003 also has the worst fit (r² = −0.07,
  literally worse than horizontal). So nsr003 has no fittable γ
  to test. The null result there is uninformative.
- For the 4 subjects with meaningful γ-fits, the beat-interval null
  **rejects**, closing the IAAFT-only-passes ambiguity from the
  n=1 pilot. The IAAFT preserves the linear amplitude spectrum,
  but the beat-interval null does NOT — so passing the latter
  while failing the former (on subjects with valid fits) is
  evidence that γ requires the **temporal ordering of beats**, not
  just the marginal RR distribution.

## 6. Honest one-line interpretation update

> **HRV at VLF on healthy adults is multifractal with moderate width
> (Δh ≈ 0.19) and γ that varies enormously per-subject (0.07 to
> 1.09). The cardiac substrate does NOT support a clean cross-substrate
> γ ≈ 1 universal — but does support a "regime marker candidate" with
> per-subject calibration required, since γ requires beat-ordered
> structure (beat-interval null rejects 4/5).**

## 7. What this DOES license

- **Substrate has multifractal structure** (Δh > 0 on all 5).
- **γ requires beat-temporal order** on subjects with fittable γ.
- **Per-subject HRV γ is a possible regime marker** — but needs
  per-subject calibration, not universal interpretation.

## 8. What this does NOT license

- **NO** universal γ ≈ 1 claim — cross-subject mean is 0.50, not 1.0.
- **NO** cross-substrate convergence support — the cardiac substrate
  is now SHOWN to be inconsistent with the universal-γ-near-1 framing.
- **NO** pathological / age / state generalisation — n=5 healthy at
  rest only.
- **NO** evidential-lane promotion — multi-subject still small,
  latent-variable null still required, contrast with pathology
  (CHF/AF) still required per owner's prioritisation.

## 9. Comparison across all 4 substrates in registry

| substrate | n | γ mean | γ std | r² | Δh | beat-null |
|---|---|---|---|---|---|---|
| FRED INDPRO (macro) | 1 | 0.94 | — | 0.52 | not run | not run |
| BTCUSDT 1h | 1 | 0.00 | — | 0.001 | not run | not run |
| HRV nsr001 (n=1 pilot) | 1 | 1.09 | — | 0.97 | not run | not run |
| **HRV NSR2DB n=5** | **5** | **0.50** | **0.44** | **0.67** | **0.19** | **4/5 sep** |

The n=5 result **supersedes** the n=1 conclusions on the cardiac
substrate. n=1 is now demonstrably an outlier sample.

## 10. Next steps (per owner's prioritisation, completed: MFDFA + beat-null)

1. ~~MFDFA on 5 subjects~~ ✓ this PR
2. ~~Beat-interval null on same 5~~ ✓ this PR
3. **Pathology contrast** (next): CHF DB (chfdb), AF DB (afdb) on
   PhysioNet. Compare γ and Δh between healthy NSR2DB and
   pathological cohorts. Without contrast γ = 0.50 ± 0.44 is
   statistically descriptive but not a marker.
4. **Multi-subject scale** (later): nsr006-nsr054 + Fantasia +
   chfdb/afdb. Only after methodology is closed.

## 11. Revised claim per CLAIM_BOUNDARY.md

The cardiac substrate's contribution to γ-program §3.2 cross-substrate
convergence framing is now formally **negative** at the n=5 pilot
level. Specifically:

- The substrate is multifractal (Δh > 0).
- γ is highly variable per subject; mean ≠ 1.
- Beat-temporal structure is required (beat-null rejects).

The "regime marker candidate" framing remains valid IF and ONLY IF
the marker is interpreted per-subject (not universal). For a
cross-substrate convergence statement, this substrate currently
provides **non-supportive evidence**.

## 12. Replication

```bash
pip install wfdb scipy numpy
python run_nsr2db_hrv_multifractal.py
```

5 subjects × MFDFA × 30 beat-null surrogates × 20000-RR truncation.
Runtime ~2 min. Determinism: seed=42 + immutable PhysioNet records.

---

**claim_status:** measured (about this report)
**γ-claim status (HRV cardiac substrate):** hypothesized → narrowed
to per-subject marker candidate; cross-substrate convergence support
NOT licensed
**result_json:** evidence/replications/physionet_nsr2db_multifractal/result.json
**run_log:** evidence/replications/physionet_nsr2db_multifractal/run.log
