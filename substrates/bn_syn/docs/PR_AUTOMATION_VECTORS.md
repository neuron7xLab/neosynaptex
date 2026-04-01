# PR Test Automation Vectors (anti-manual mismatch strategy)

Ціль: прибрати «банальні» невідповідності перед merge через автоматичні guardrails, а не ручний review.

## Найбільш ефективні вектори (пріоритет)

1. **SSOT-синхронізація статус-чеків**
   - Джерело істини: `.github/PR_GATES.yml`.
   - Похідний артефакт: `.github/REQUIRED_STATUS_CONTEXTS.yml`.
   - Автоматизація: `scripts/sync_required_status_contexts.py` + `--check` у gate.
   - Ефект: прибирає ручні правки після змін job names / required checks.

2. **Fail-fast для governance-інваріантів PR**
   - `validate_pr_gates` + `validate_required_status_contexts` в локальному `pre-push` і в CI.
   - Ефект: помилки виявляються до відкриття PR, а не після рев’ю.

3. **Авто-ремедіація типових drift-проблем**
   - Для локальної розробки запускати `python -m scripts.sync_required_status_contexts`.
   - Для CI: тільки `--check` (щоб не мутувати репозиторій у pipeline).
   - Ефект: dev отримує просту, детерміновану команду для виправлення.

4. **Короткий цикл валідації для авторів PR**
   - Обов’язковий пакет: `make ssot` + smoke tests.
   - Ефект: зменшує повторні «повернення» PR на дрібні невідповідності.

## Що вже інтегровано

- Доданий синхронізатор required status contexts:
  - `python -m scripts.sync_required_status_contexts`
  - `python -m scripts.sync_required_status_contexts --check`
- `make ssot` тепер перевіряє:
  - `validate_pr_gates`
  - `validate_required_status_contexts`
  - `sync_required_status_contexts --check`
- `scripts/pre-push.sh` включає ті самі перевірки, щоб ловити проблеми до push.

## Рекомендована операційна практика

- Перед push:
  1. `python -m scripts.sync_required_status_contexts`
  2. `make ssot`
  3. `pytest -m "not validation" -q`
- У CI лишити тільки перевірку консистентності (`--check`) без автозапису.

## KPI для контролю, що автоматизація працює

- Частка PR із падінням через `REQUIRED_STATUS_CONTEXTS_MISMATCH` (має йти до 0).
- Медіанний час від першого CI run до зеленого PR (має зменшитись).
- Кількість ручних правок у `.github/*` після review (має зменшитись).
