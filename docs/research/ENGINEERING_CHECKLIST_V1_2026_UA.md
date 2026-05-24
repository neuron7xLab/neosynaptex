# RESEARCH · ENGINEERING CHECKLIST v1.1 (2026)

## Статус документа

- **Protocol ID:** `NEOSYNAPTEX-PROTOCOL-v1.1`
- **Status:** ACTIVE
- **Призначення:** операційний і machine-readable сумісний governance-чеклист для PR/CI.
- Canonical JSON для CI-інтеграції винесено в `docs/research/NEOSYNAPTEX_PROTOCOL_V1_1.json`.

---

## 0) Six-File Methodology (contract-first execution)

Перед генерацією коду зміни проходять через 6 обов’язкових артефактів. Ідея: спочатку фіксуємо контракти, інваріанти та межі, потім імплементація.

1. `01_problem.md` — одна фраза проблеми + falsification condition (`PRE-01`).
2. `02_contract.yaml` — I/O, типи, boundary conditions (`PRE-02`).
3. `03_invariants.yaml` — інваріанти, метрики, допустимі діапазони (`MATH-01`, `MATH-02`).
4. `04_test_plan.md` — red→green, contract coverage, adversarial cases (`VAL-01..03`).
5. `05_governance.md` — human impact, rollback/kill-switch, CI mapping IDs (`GOV-01..03`).
6. `06_change_plan.md` — мінімальний план імплементації без зайвого коду (`IMPL-01..03`).

**Gate rule:** якщо будь-який із 6 файлів відсутній або неповний, імплементація не починається.

---

## 1) Деідеологізація: що прибрано з validation-layer

Щоб уникнути overclaim і декоративної псевдоформалізації, цей протокол **не використовує як gate**:

- “Principle of Least Action” у метафоричному сенсі для архітектури.
- “Сімка” як маркер стійкості без формальної метрики.
- `γ≈1.0` як універсальний “золотий режим” без estimator/CI/null/boundary.

Ці формулювання можуть існувати лише як дослідницький контекст (DECORATIVE), але не як критерій merge-ready.

---

## 2) Severity model

- **BLOCKER** — обов’язково до merge; порушення = CI fail.
- **ADVISORY** — бажано; відхилення вимагає explicit override в PR.
- **DECORATIVE** — естетичне або нефункціональне; не допускається як validation gate.

---

## 3) Checklist schema (ID-first)

### PRE-WORK

- [ ] **PRE-01 (BLOCKER) · Falsifiable Hypothesis**  
      Проблема сформульована як falsifiable-гіпотеза з явною умовою спростування.  
      **Enforcement:** PR містить секцію `Falsification Condition`.

- [ ] **PRE-02 (BLOCKER) · Contract Definition**  
      Визначено I/O, типи, boundary conditions до імплементації.  
      **Enforcement:** явні type hints та boundary checks у цільовому модулі.

- [ ] **PRE-03 (BLOCKER) · Six-File Presence Gate**  
      Усі 6 методологічних файлів присутні й не порожні (`01_problem.md`...`06_change_plan.md`).  
      **Enforcement:** CI script `tools/audit/check_six_file_presence.py` + JSON report.

### MATH

- [ ] **MATH-01 (BLOCKER) · Dimensional Consistency**  
      Узгоджені розмірності/одиниці всіх змінних у формулах.  
      **Enforcement:** machine-readable `dimension_check_report.json` (PASS/FAIL) з CI-аудиту.

- [ ] **MATH-02 (BLOCKER) · No Magic Numbers**  
      Жодних “магічних” коефіцієнтів без виводу або параметризації.  
      **Enforcement:** lint/review rule для hardcoded numeric constants (крім `0`, `1`, `-1`) поза конфігом.

### IMPLEMENTATION

- [ ] **IMPL-01 (BLOCKER) · Single Responsibility**  
      Один модуль — одна основна публічна відповідальність.  
      **Enforcement:** static-analysis/review на надлишковий export-surface.

- [ ] **IMPL-02 (BLOCKER) · Minimal Sufficient Code**  
      Не 100 рядків там, де достатньо 10; кожен блок підсилює контракт/інваріант.  
      **Enforcement:** code review: без boilerplate і зайвих абстракцій.

- [ ] **IMPL-03 (BLOCKER) · Isolated Side Effects**  
      Побічні ефекти локалізовані; мутації стану явні.  
      **Enforcement:** purity/side-effect checks там, де застосовно.

### VALIDATION

- [ ] **VAL-01 (BLOCKER) · Red-Green Cycle**  
      Тест падає до фіксу (red→green).  
      **Enforcement:** PR містить секцію `Red-Green Evidence` з посиланням на failing CI run URL та passing run URL.

- [ ] **VAL-02 (BLOCKER) · Contract Coverage**  
      Покриття контракту, не рядків; для core logic — property-based підхід.  
      **Enforcement:** Hypothesis (або еквівалент) для релевантних модулів.

- [ ] **VAL-03 (BLOCKER) · Adversarial Input**  
      Протестовано edge/malformed input.  
      **Enforcement:** fuzz/adversarial tests в CI.

### FALSIFICATION

- [ ] **FALS-01 (BLOCKER) · Independent Verification Protocol**  
      Валідація через незалежний тестовий контур / harness, не консенсус моделей.  
      **Enforcement:** окремий validation script або незалежний test-suite артефакт у PR.

- [ ] **FALS-02 (ADVISORY) · Negative Result Documentation**  
      Негативні результати збережені як інженерні дані.  
      **Enforcement:** лог/секція документації про відхилені гіпотези.

> Примітка: “інша модель/агент” допускається як **adversarial review**, але не як самодостатній falsification evidence.

### ARTIFACT

- [ ] **ART-01 (BLOCKER) · Documentation as Contract**  
      README/документи читаються як операційний контракт.  
      **Enforcement:** documentation review block.

- [ ] **ART-02 (BLOCKER) · Reproducible Environment**  
      Відтворення в 1 команду + фіксовані seed/dependency boundaries.  
      **Enforcement:** CI build from scratch з lockfile/manifest.

- [ ] **ART-03 (ADVISORY) · Tool-Agnostic Artifacts**  
      Артефакти не залежать від конкретного вендор-агента.  
      **Enforcement:** `Invariants.yaml` рекомендовано; `CLAUDE.md` не є BLOCKER-вимогою.

### GOVERNANCE

- [ ] **GOV-01 (BLOCKER) · Human-in-the-Loop Safety**  
      Significant changes містять оцінку впливу на людину (безпека, агентність, ризик виключення).  
      **Enforcement:** PR checklist item `Human Impact Assessment`.

- [ ] **GOV-02 (BLOCKER) · Emergency Exit**  
      Rollback/kill-switch шлях задокументовано та перевірено.  
      **Enforcement:** rollback script/state-reversal evidence.

- [ ] **GOV-03 (BLOCKER) · CI Failure Mapping**  
      Кожен CI fail прив’язаний до checklist ID до внесення фіксу.  
      **Enforcement:** commit message / PR note містить ID (`PRE-*`, `VAL-*`, `GOV-*`, ...).

---

## 4) CI Failure Protocol

1. CI падає (`exit code != 0`) → execution halt.  
2. Інцидент класифікується по `checklist ID` та severity.  
3. Для high-impact змін додається `Six-File Evidence` з 6 шляхами артефактів.  
4. Фікс заборонений до ідентифікації порушеного інваріанта.  
5. Merge дозволений лише якщо всі **BLOCKER = PASS**.

Рекомендований формат нотатки у PR:

```text
CI Failure Mapping:
- failure: <short description>
- checklist_id: <e.g., VAL-03>
- severity: <BLOCKER|ADVISORY|DECORATIVE>
- fix_plan: <one paragraph>
```

Додатково до CI Failure Mapping, для змін high-impact додавайте посилання на Six-File артефакти:

```text
Six-File Evidence:
- problem: docs/research/01_problem.md
- contract: docs/research/02_contract.yaml
- invariants: docs/research/03_invariants.yaml
- test_plan: docs/research/04_test_plan.md
- governance: docs/research/05_governance.md
- change_plan: docs/research/06_change_plan.md
```

---

## 5) Cost Function Optimization Rule

Архітектурні рішення мають демонструвати мінімізацію latency/compute **за збереження необхідної точності**.  
Будь-який tunable parameter (включно з `γ`) повинен мати:

- estimator definition,
- confidence interval / uncertainty estimate,
- null/surrogate baseline,
- boundary of applicability (на якому substrate/режимі валідно).

Без цього параметр вважається **DECORATIVE**, а не доказовим.

---

## 6) Final merge condition

- Усі **BLOCKER** пункти — `PASS`.
- Для **ADVISORY** або `override` в PR є явне обґрунтування.
- **DECORATIVE** твердження не використовуються для approval.

Якщо хоча б один BLOCKER не тримається — **not done**.

---

**Дисципліна = пройдений протокол.**


---

## 7) Machine-readable protocol payload (canonical JSON)

> Нижче — канонічний JSON payload для інтеграції в автоматизовані policy checks.

```json
{
  "protocol_id": "NEOSYNAPTEX-PROTOCOL-v1.1",
  "status": "ACTIVE",
  "severity_levels": {
    "BLOCKER": "Must be resolved before merge. Fails CI pipeline.",
    "ADVISORY": "Recommended practice. Requires explicit override in PR description if violated.",
    "DECORATIVE": "Aesthetic or non-functional. Must be removed from validation layers."
  },
  "checklist_schema": [
    {
      "id": "PRE-01",
      "category": "PRE-WORK",
      "severity": "BLOCKER",
      "invariant": "Falsifiable Hypothesis",
      "description": "The problem must be stated as a falsifiable hypothesis. The condition for refutation must be explicit.",
      "enforcement": "PR description must contain a 'Falsification Condition' section."
    },
    {
      "id": "PRE-02",
      "category": "PRE-WORK",
      "severity": "BLOCKER",
      "invariant": "Contract Definition",
      "description": "I/O, types, and boundary conditions must be defined before implementation.",
      "enforcement": "Explicit type hints and boundary checks implemented in the target module."
    },
    {
      "id": "PRE-03",
      "category": "PRE-WORK",
      "severity": "BLOCKER",
      "invariant": "Six-File Presence Gate",
      "description": "All six methodology files must exist and be non-empty before implementation starts.",
      "enforcement": "CI script check_six_file_presence.py emits a machine-readable PASS/FAIL report."
    },
    {
      "id": "MATH-01",
      "category": "MATH",
      "severity": "BLOCKER",
      "invariant": "Dimensional Consistency",
      "description": "All variables in equations must have consistent physical/computational dimensions.",
      "enforcement": "Machine-readable dimension_check_report.json (PASS/FAIL) generated in CI."
    },
    {
      "id": "MATH-02",
      "category": "MATH",
      "severity": "BLOCKER",
      "invariant": "No Magic Numbers",
      "description": "All coefficients must be derived or explicitly defined as tunable parameters.",
      "enforcement": "Linting and review rules rejecting hardcoded numeric constants (excluding 0, 1, -1) outside configuration layers."
    },
    {
      "id": "IMPL-01",
      "category": "IMPLEMENTATION",
      "severity": "BLOCKER",
      "invariant": "Single Responsibility",
      "description": "One module exports only one primary public interface.",
      "enforcement": "Static analysis or review constraint on the public export surface."
    },
    {
      "id": "IMPL-02",
      "category": "IMPLEMENTATION",
      "severity": "BLOCKER",
      "invariant": "Minimal Sufficient Code",
      "description": "Code volume does not equal value. Every block must reinforce a contract or invariant.",
      "enforcement": "Code review phase enforcing zero boilerplate and minimal necessary abstractions."
    },
    {
      "id": "IMPL-03",
      "category": "IMPLEMENTATION",
      "severity": "BLOCKER",
      "invariant": "Isolated Side Effects",
      "description": "State mutations must be explicit and localized.",
      "enforcement": "Functional purity and side-effect isolation checks."
    },
    {
      "id": "VAL-01",
      "category": "VALIDATION",
      "severity": "BLOCKER",
      "invariant": "Red-Green Cycle",
      "description": "Tests must fail before the fix is applied.",
      "enforcement": "PR must include Red-Green Evidence with links to one failing CI run and one passing CI run."
    },
    {
      "id": "VAL-02",
      "category": "VALIDATION",
      "severity": "BLOCKER",
      "invariant": "Contract Coverage",
      "description": "Tests must cover the defined contract, not just line execution.",
      "enforcement": "Mandatory integration of property-based testing (e.g., Hypothesis) for core logic modules."
    },
    {
      "id": "VAL-03",
      "category": "VALIDATION",
      "severity": "BLOCKER",
      "invariant": "Adversarial Input",
      "description": "System must gracefully handle edge cases and intentionally malformed inputs.",
      "enforcement": "Fuzz or adversarial testing execution within the CI pipeline."
    },
    {
      "id": "FALS-01",
      "category": "FALSIFICATION",
      "severity": "BLOCKER",
      "invariant": "Independent Verification Protocol",
      "description": "Results must be verified through an independent test harness, not agent consensus.",
      "enforcement": "Requirement of an isolated validation script or a standalone test-suite artifact in the PR. External agents are restricted to adversarial review roles only."
    },
    {
      "id": "FALS-02",
      "category": "FALSIFICATION",
      "severity": "ADVISORY",
      "invariant": "Negative Result Documentation",
      "description": "Failed hypotheses must be documented as valuable engineering data.",
      "enforcement": "Dedicated section in documentation or logs detailing rejected design pathways."
    },
    {
      "id": "ART-01",
      "category": "ARTIFACT",
      "severity": "BLOCKER",
      "invariant": "Documentation as Contract",
      "description": "README and associated documentation must read as binding operational contracts.",
      "enforcement": "Documentation review block check."
    },
    {
      "id": "ART-02",
      "category": "ARTIFACT",
      "severity": "BLOCKER",
      "invariant": "Reproducible Environment",
      "description": "Execution must be reproducible via a single command and fixed seeds/dependencies.",
      "enforcement": "CI build from scratch enforced via lockfiles or strict dependency manifests."
    },
    {
      "id": "ART-03",
      "category": "ARTIFACT",
      "severity": "ADVISORY",
      "invariant": "Tool-Agnostic Artifacts",
      "description": "Artifacts must not depend permanently on vendor-specific or agent-specific layouts.",
      "enforcement": "'Invariants.yaml' recommended; 'CLAUDE.md' is demoted to a non-BLOCKER advisory file."
    },
    {
      "id": "GOV-01",
      "category": "GOVERNANCE",
      "severity": "BLOCKER",
      "invariant": "Human-in-the-Loop Safety",
      "description": "Significant changes must assess impact on human agency and safety. Structural modifications cannot degrade human control.",
      "enforcement": "Mandatory PR checklist field: 'Human Impact Assessment'."
    },
    {
      "id": "GOV-02",
      "category": "GOVERNANCE",
      "severity": "BLOCKER",
      "invariant": "Emergency Exit",
      "description": "Kill-switch or rollback path must be documented and tested.",
      "enforcement": "Presence of rollback scripts or state-reversal functions."
    },
    {
      "id": "GOV-03",
      "category": "GOVERNANCE",
      "severity": "BLOCKER",
      "invariant": "CI Failure Mapping",
      "description": "Every CI failure must be explicitly mapped to a specific checklist ID before fixing.",
      "enforcement": "Commit message regex enforcing checklist ID reference."
    }
  ],
  "execution_rules": {
    "CI_FAILURE_PROTOCOL": "Step 1: Halt on CI failure (exit code != 0). Step 2: Map failure to checklist_id and severity. Step 3: For high-impact changes, attach Six-File Evidence paths. Step 4: Do not apply fixes until violated invariant is identified. Step 5: Merge only when all BLOCKER checks pass.",
    "MERGE_CONDITION": "All BLOCKER invariants must return PASS. Any failure prohibits merge.",
    "COST_FUNCTION_OPTIMIZATION": "Design decisions must demonstrably minimize system latency/compute while maintaining required accuracy/precision. Tunable parameters (e.g., γ) must have defined estimators."
  }
}
```

## 8) Semantic anti-bullshit gate (content quality)

Щоб уникнути «ілюзії детермінізму» (коли непорожній файл проходить CI без змістовної цінності), вводиться `SEM-01`:

- Скрипт: `tools/audit/check_six_file_semantics.py`
- Репорт: `artifacts/audit/six_file_semantics_report.json`
- Правило: `SEM-01` має бути `PASS` для merge-ready статусу BLOCKER-контурів.

`SEM-01` перевіряє не лише наявність, а мінімальну змістову валідність: falsification section, contract keys, invariant pass-conditions, red/green evidence fields, governance mapping, і структурований change plan.

---

## 8) First-principles & value-function alignment

Щоб PR-архітектура не деградувала в формалізм, зміни мають бути прив’язані до першопринципів і функцій цінності ядра системи.

- Специфікація: `docs/research/07_first_principles_value_function.yaml`
- Аудит-скрипт: `tools/audit/check_value_architecture_mapping.py`
- Audit-репорт: `artifacts/audit/value_architecture_report.json`

`ARCH-01` = PASS є обов’язковою ознакою того, що структура PR узгоджена з ціннісною логікою системи.

---

