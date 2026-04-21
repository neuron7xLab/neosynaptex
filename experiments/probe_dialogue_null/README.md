# Why dialogue γ-probe failed AT battery

**Hypothesis:** `K ~ C^(-γ)` on cumulative vocab/entropy vs cumulative token count detects criticality in dialogue.

**Result:** 0/5 real sessions passed AT battery.

**Root cause:** cumulative observables are monotonic by construction. All working neosynaptex substrates use windowed non-monotonic observables (BnSyn, Kuramoto, HRV). γ measures dynamic fluctuation ratio, not cumulative accumulation. No theoretical prediction for γ≈1 in dialogue exists (unlike BnSyn σ=1 or Kuramoto K_c).

**Conclusion:** lexical proxy insufficient. Valid dialogue substrate requires windowed non-monotonic observable with theoretical γ prediction (Zipf, avalanche distributions). Future work only.

**Evidence:** [at_report_v1.json](at_report_v1.json), [at_report_v2.json](at_report_v2.json)
