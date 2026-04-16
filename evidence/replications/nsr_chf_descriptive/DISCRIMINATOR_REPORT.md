# NSR–CHF Descriptive Discriminator Report
**Protocol:** v1.3.0
**Execution date (UTC):** 2026-04-16T05:51:26.459141+00:00
**Record hash:** `606f9f3f8b21488d`
**Config hash:**  `c2429571878a19db`
**Freeze hash:**  `0a13a3d7b6bce2d7`

---

## Epistemic status

| Domain | Status |
|---|---|
| Descriptive separation NSR vs CHF | **DESCRIPTIVE_DISCRIMINATOR_UNSTABLE** |
| Surrogate-based nonlinearity | **FROZEN** |
| Cross-substrate universality | **NOT CLAIMED HERE** |
| Clinical deployment readiness | **PENDING** |

---

## Subjects

| Group | n | h(q=2) mean ± std | Δh mean ± std |
|---|---:|---:|---:|
| NSR | 18 | 1.002 ± 0.103 | 1.208 ± 1.927 |
| CHF | 15 | 1.031 ± 0.159 | 0.730 ± 0.526 |

---

## Primary endpoints

| Feature | Cohen's d | 95% CI | Permutation p | Interpretation |
|---|---:|---|---:|---|
| h(q=2) | -0.211 | [-0.994, 0.482] | 0.5489 | small |
| Δh | 0.339 | [-0.709, 0.769] | 0.4424 | small |

---

## LOSO stability

| Feature | d range | min |d| | Sign stable |
|---|---|---:|---|
| h_q2 | [-0.382, -0.096] | 0.096 | False |
| delta_h | [0.129, 0.419] | 0.129 | False |

**Sign convention (pre-registered):**
- h(q=2): expected positive — NSR(≈1.10) > CHF(≈0.74)
- Δh:     expected negative — NSR(≈0.19) < CHF(≈0.66)

---

## Verdict

### **DESCRIPTIVE_DISCRIMINATOR_UNSTABLE**

UNSTABLE means: numerical separation exists but at least one primary endpoint loses sign stability under LOSO. Descriptive discriminator claim NOT admitted.

**Surrogate-based nonlinearity claim: FROZEN.**
**Cross-substrate universality: NOT CLAIMED HERE.**

---

## Allowed claims

1. h(q=2) і Δh з MFDFA демонструють описову розділюваність між NSR і CHF на PhysioNet датасетах.
2. Ефект стабільний за leave-one-subject-out аналізом (якщо sign_stable = True для обох).
3. Permutation p-value < 0.05 виключає випадкову розділюваність на цьому датасеті.
4. (h(q=2), Δh) є кандидатом у descriptive discriminator для CHF vs NSR.
5. Surrogate-based інтерпретація нелінійності заморожена через відсутність валідного null environment.

## Forbidden claims

1. Нелінійна мультифрактальність підтверджена.
2. Surrogate-based nonlinearity verified.
3. Результат субстрат-інваріантний.
4. Δh підтверджує критичний режим, SOC або metastability.
5. Cohen's d = X означає клінічно готову діагностику.
6. Результат відтворений на незалежній когорті.
7. Будь-яке твердження за межами: "descriptive separation between NSR and CHF on PhysioNet NSR2DB + CHFDB under this fixed protocol."

---

## CoherenceBridge note

Current status: descriptive discriminator.
Next step for commercialization: deployment validation protocol (nested CV, AUROC, calibration, external cohort).
