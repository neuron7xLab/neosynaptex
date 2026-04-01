# CODEX FEEDBACK (UA): evidence-bound оцінка поточного стану BN-Syn

**Дата:** 2026-02-06  
**Статус:** fail-closed оцінка лише за доказами в репозиторії та зафіксованими локальними прогонами.

## Evidence Index

### Файлові джерела (SSOT / контракти / CI)
- `CODEBASE_READINESS.md` — формальна модель scoring, категорії, критерії PASS/PARTIAL/FAIL.
- `docs/API_CONTRACT.md` — задекларований stable API surface.
- `quality/api_contract_baseline.json` — baseline для API contract gate.
- `scripts/check_api_contract.py` — реалізація semver-aware API contract checker.
- `Makefile` — canonical target `api-contract`.
- `.github/workflows/ci-pr-atomic.yml` — PR SSOT gate з `make api-contract`.
- `docs/TESTING.md` — canonical локальний запуск API contract check.
- `requirements-lock.txt` — pinned dependencies.
- `docs/RELEASE_PIPELINE.md` — release pipeline runbook.
- `benchmarks/` + `.github/workflows/benchmarks.yml` — performance tooling + workflow.

### Локальні артефакти запусків
- `artifacts/local_runs/api_contract.log`
- `artifacts/local_runs/test.log`

## Method (точні команди)

Виконано з кореня репозиторію:

```bash
python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json
pytest -q tests/test_api_contract_command.py
```

Canonical entrypoint для перевірки API-контракту: `python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json`.  
Wrapper для CI/dev: `make api-contract`.

## Findings (лише підтверджені факти)

1. **Pre-fix проблема була відтворювана:** API-contract check падав із `ModuleNotFoundError: No module named 'bnsyn'` без ручного `PYTHONPATH`.
2. **Post-fix команда працює без ручного `PYTHONPATH`:** `python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json` завершується успішно.
3. **Визначено canonical entrypoint:** `python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json` працює з кореня репозиторію без ручного `PYTHONPATH`.
4. **Автоматична перевірка додана:** `pytest` subprocess-тест підтверджує `exit code == 0` для canonical entrypoint з чистим оточенням (без `PYTHONPATH`).
5. **Wrapper узгоджений:** `make api-contract` викликає той самий canonical entrypoint для CI/dev-паритету.

## Readiness Rubric (fail-closed розрахунок)

> Політика: якщо повний критерій категорії не доведений артефактами/запусками в цьому аудиті, ставиться `PARTIAL` або `UNKNOWN`.

| Категорія | Вага | Статус | Фактор | Пояснення |
|---|---:|---|---:|---|
| API contract readiness | 25 | PASS | 1.0 | Доведено наявність контракту, baseline, checker, CI gate + локальний pass. |
| Stability & determinism | 25 | PARTIAL | 0.5 | Є pass subset determinism тестів, але не проведено повний контур validation/property/CI replay в межах цього аудиту. |
| Reproducibility | 20 | PARTIAL | 0.5 | Є lock file і частина reproducibility checks, але без повного end-to-end reproducibility audit. |
| Documentation readiness | 15 | PARTIAL | 0.5 | Наявні runbooks/контракти, але повна doc-audit перевірка не виконувалась у цьому циклі. |
| Performance readiness | 15 | PARTIAL | 0.5 | Наявні benchmark artifacts/workflows, але benchmark suite у цьому аудиті не проганялась. |

**Обчислення:**  
`25*1.0 + 25*0.5 + 20*0.5 + 15*0.5 + 15*0.5 = 62.5`

**Результат за політикою `CODEBASE_READINESS.md`: `Advisory gap` (60 ≤ score < 80).**

## Ризики та next actions (мінімальні, high-impact)

1. **Закрити PARTIAL по determinism/reproducibility/performance** одним відтворюваним gate-run (локально або CI-артефактами), після чого перерахувати rubric без припущень.
2. **Зберігати canonical одну команду для API-contract (`python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json`)**; `make api-contract` використовувати як обгортку.
3. **Для кожного майбутнього readiness claim** додавати пряме посилання на файл-джерело та/або артефакт логу запуску.
