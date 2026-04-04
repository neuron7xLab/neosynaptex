# Validation Gap Remediation Playbook

## Purpose

Цей документ закриває практичні прогалини в локальній валідації, які були виявлені під час перевірки документаційного дифу.

Ціль: перетворити статуси `⚠️` у керований engineering-plan з чіткими командами, критеріями приймання та контрольними артефактами.

---

## 1) Gap Register (Observed)

| Gap | Observed symptom | Probable class | Immediate impact |
|---|---|---|---|
| G1: `pylint` unavailable | `pylint: command not found` | toolchain drift | неможливо виконати project lint contract повністю |
| G2: strict `mypy` import failures | масові `import-not-found` | package layout / path resolution mismatch | strict typing gate непрозорий для рев’ю |
| G3: `python -m build` missing module | `No module named build` | missing packaging tool in env | неможливо локально верифікувати build step |
| G4: pytest collection import errors | `tests.fixtures`, `tests.tolerances`, `contracts.assert_dt_stability` | тестова структура/імпорт-контракт дрейф | smoke gate зупиняється до runtime assertions |

---

## 2) Remediation Strategy (Operational)

### G1 — Pylint Toolchain Restoration

**Action path**

1. Додати `pylint` до dev toolchain lock (`requirements-dev` / project tooling spec).
2. Зафіксувати version pin, сумісний із Python 3.12.
3. Додати preflight check у CI (verify tool availability before lint run).

**Acceptance criteria**

- `pylint src/bnsyn` запускається без `command not found`.
- CI журнал містить явну версію pylint.

### G2 — Mypy Strict Import Surface Repair

**Action path**

1. Провести inventory існуючих `bnsyn.*` модулів vs imports у `src/bnsyn`.
2. Усунути розриви package-path (структура каталогів, `__init__.py`, module aliases).
3. Зафіксувати policy для optional modules (або реальні модулі, або explicit typing stubs).

**Acceptance criteria**

- `mypy src --strict --config-file pyproject.toml` проходить без `import-not-found` для core package.
- Missing-import exceptions (якщо є) документовані та мінімізовані.

### G3 — Build Pipeline Tool Availability

**Action path**

1. Додати `build` до deterministic dev environment setup.
2. Додати `python -m build` у локальний preflight script.
3. Перевірити, що build artifact metadata узгоджена з package layout.

**Acceptance criteria**

- `python -m build` завершується успішно.
- Створені sdist/wheel артефакти валідні.

### G4 — Pytest Collection Contract Recovery

**Action path**

1. Вирівняти test package resolution (`tests` imports) з фактичною структурою.
2. Верифікувати наявність/експорт `tests.fixtures`, `tests.tolerances`, `contracts.assert_dt_stability`.
3. Додати import-contract smoke test до CI (collection-only guard).

**Acceptance criteria**

- `python -m pytest -m "not (validation or property)" -q` проходить collection phase без import errors.
- Подальші падіння (якщо будуть) уже відносяться до фактичної логіки тестів, а не інфраструктури імпортів.

---

## 3) Execution Order (Recommended)

1. **Toolchain first:** G1 + G3.
2. **Import surface:** G4.
3. **Type strictness stabilization:** G2.
4. **Gate hardening:** об’єднати всі чотири перевірки в єдиний локальний/CI preflight.

Цей порядок мінімізує шум: спочатку відновлюється інструментарій, далі виправляється import-contract, і лише потім стабілізується strict typing.

---

## 4) CI Hardening Proposal

Додати окремий workflow stage `validation-preflight`:

1. verify tool presence (`pylint`, `mypy`, `build`, `pytest`),
2. run import-collection smoke,
3. run strict typecheck,
4. run lint,
5. run build.

Кожен крок має explicit fail reason, щоб уникнути змішування "tool missing" та "code issue" в одному шумному логі.

---

## 5) Reviewer Packet Template (for this gap class)

Після remediation рев’ю-пакет має містити:

- tool versions snapshot,
- mypy summary (error class delta before/after),
- pytest collection report,
- build artifact manifest,
- короткий risk statement про залишкові обмеження.

---

## 6) Scope Boundary

Цей playbook є **документаційним і операційним планом**. Він не змінює runtime логіку BN-Syn, canonical proof path або наукові claim boundaries.
