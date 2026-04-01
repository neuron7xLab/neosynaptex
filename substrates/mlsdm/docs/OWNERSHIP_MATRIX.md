# Матриця відповідальності пакетів MLSDM

Цей документ фіксує відповідальність пакетів `src/mlsdm/`, їхні основні контракти (публічні інтерфейси/моделі) та ключові документи, на які вони спираються.

## Ключові специфікації

- [Architecture Specification](ARCHITECTURE_SPEC.md)
- [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md)

## Пакети `src/mlsdm/`

| Пакет | Відповідальність | Основні контракти | Ключові документи |
| --- | --- | --- | --- |
| `adapters` | Інтеграція з провайдерами LLM та фабрика адаптерів. | `llm_provider.py`, `provider_factory.py`, адаптери `openai_adapter.py`, `anthropic_adapter.py`, `local_stub_adapter.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `api` | HTTP API шар (FastAPI застосунок, життєвий цикл, middleware, схеми). | `app.py`, `lifecycle.py`, `health.py`, `schemas.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `cli` | CLI входи для локального запуску/керування. | `main.py`, `__main__.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `cognition` | Когнітивні контури: моральні фільтри, рольові межі, онтологічний матчинг. | `moral_filter.py`, `moral_filter_v2.py`, `role_boundary_controller.py`, `ontology_matcher.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `config` | Конфігурація, калібрування, runtime параметри, архітектурний маніфест. | `default_config.yaml`, `architecture_manifest.py`, `runtime.py`, `calibration.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `contracts` | Спільні моделі та типи контрактів для API/движка/мовлення. | `engine_models.py`, `speech_models.py`, `errors.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `core` | Когнітивне ядро: контролер, пайплайн LLM, менеджер памʼяті. | `cognitive_controller.py`, `llm_wrapper.py`, `llm_pipeline.py`, `memory_manager.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `deploy` | Оркестрація деплойменту (канарні релізи). | `canary_manager.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `engine` | Композиція когнітивного движка та фабрики. | `neuro_cognitive_engine.py`, `factory.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `entrypoints` | Точки входу для різних режимів запуску (agent/cloud/dev/service). | `serve.py`, `agent_entry.py`, `cloud_entry.py`, `dev_entry.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `extensions` | Розширення поведінки (NeuroLang). | `neuro_lang_extension.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `memory` | Багаторівнева памʼять, фазова латентність, сховища. | `multi_level_memory.py`, `phase_entangled_lattice_memory.py`, `store.py`, `sqlite_store.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `neuro_ai` | Нейрокогнітивні адаптери та prediction-error контури. | `contract_api.py`, `contracts.py`, `prediction_error.py`, `adapters.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `observability` | Метрики, логування, телеметрія, трасування. | `metrics.py`, `logger.py`, `tracing.py`, `exporters.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `router` | Маршрутизація LLM провайдерів. | `llm_router.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `rhythm` | Когнітивний ритм та режими циклів. | `cognitive_rhythm.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `sdk` | Клієнтський SDK для доступу до сервісу. | `neuro_engine_client.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `security` | Політики безпеки, guardrails, rate limiting, scrubbing. | `policy_engine.py`, `guardrails.py`, `rate_limit.py`, `payload_scrubber.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `service` | Сервісна обгортка для Neuro Engine. | `neuro_engine_service.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `speech` | Контури керування мовленням та governance. | `governance.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `state` | Схема/зберігання стану системи та міграції. | `system_state_schema.py`, `system_state_store.py`, `system_state_migrations.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
| `utils` | Базові утиліти: конфіг-лоадери, валідація, метрики, стабілізатори. | `config_loader.py`, `config_validator.py`, `input_validator.py`, `errors.py`. | [Architecture Specification](ARCHITECTURE_SPEC.md), [NeuroCognitiveEngine Spec](NEURO_COG_ENGINE_SPEC.md) |
