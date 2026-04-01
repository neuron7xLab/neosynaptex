# NeuroCognitiveEngine — Integrated MLSDM + FSLGS Layer

## Purpose

Надати єдину точку входу (`NeuroCognitiveEngine`), яка:

- використовує `MLSDM.core.LLMWrapper` як когнітивний субстрат (пам'ять, ритм, мораль, резилієнтність);
- опційно включає `FSLGSWrapper` як мовний наглядач (dual-stream, UG, anti-schizo, fractal language memory).

## High-level Flow

1. Клієнт викликає `NeuroCognitiveEngine.generate(...)`.
2. Якщо FSLGS доступний:
   - FSLGS:
     - оцінює режим (rest/action),
     - робить dual-stream (семантика/послідовність),
     - перевіряє UG та асоціативну когерентність,
     - будує `enhanced_prompt`.
   - Для генерації FSLGS викликає адаптер `governed_llm`, який:
     - делегує виклик у `MLSDM.LLMWrapper.generate(...)`,
     - зберігає повний стан MLSDM,
     - повертає тільки `response` як текст.
3. Якщо FSLGS вимкнений — запит йде напряму в `LLMWrapper.generate(...)`.
4. `NeuroCognitiveEngine` повертає:
   - `response` — фінальний текст,
   - `governance` — сирий вихід FSLGS (якщо є),
   - `mlsdm` — сирий вихід LLMWrapper.

## Integration Contract

- `llm_generate_fn(prompt: str, max_tokens: int) -> str`
- `embedding_fn(text: str) -> np.ndarray`
- Без жорсткої прив'язки до конкретного провайдера (OpenAI, Anthropic, локальна модель).
