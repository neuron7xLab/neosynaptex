# MLSDM Literature Map (Subsystem Coverage)

## Memory Core
paths: src/mlsdm/memory/, src/mlsdm/state/, tests/property/test_multilevel_synaptic_memory_properties.py
citations: [@benna2016_synaptic] [@fusi2005_cascade] [@olafsdottir2018_replay]
rationale: Synaptic consolidation and forgetting dynamics in Benna & Fusi and Fusi et al. motivate the multi-level memory depth implemented in src/mlsdm/memory/. Replay-centric planning evidence (Ólafsdóttir et al.) underpins the state tracking and property tests that guard degradation across runs.

## Retrieval / Embeddings / RAG
paths: src/mlsdm/core/llm_pipeline.py, src/mlsdm/utils/embedding_cache.py, src/mlsdm/router/
citations: [@karpukhin2020_dpr] [@lewis2020_rag] [@borgeaud2022_retro]
rationale: Dense passage retrieval (Karpukhin et al.) and RAG (Lewis et al.) inform how the llm_pipeline composes retrievers with generation. Ultra-scale retrieval (Borgeaud et al.) supports caching and router fan-out to keep retrieval grounded in evidence-heavy contexts.

## Cognitive Controller / Routing
paths: src/mlsdm/core/cognitive_controller.py, src/mlsdm/router/, src/mlsdm/extensions/neuro_lang_extension.py
citations: [@yao2022_react] [@schick2023_toolformer] [@park2023_generative]
rationale: ReAct (Yao et al.) and Toolformer (Schick et al.) justify controller-driven routing between tools and language reasoning. Generative agent orchestration (Park et al.) backs the extension and router hooks that schedule multi-turn behaviors.

## Cognitive Rhythm / Sleep-Wake
paths: src/mlsdm/rhythm/, src/mlsdm/core/memory_manager.py, src/mlsdm/core/cognitive_controller.py, tests/unit/test_cognitive_rhythm.py
citations: [@hastings2018_circadian] [@mendoza2009_clocks] [@olafsdottir2018_replay]
rationale: Circadian control mechanisms (Hastings et al.; Mendoza) motivate phase-aware scheduling of cognitive processing, while replay dynamics (Ólafsdóttir et al.) align with alternating consolidation and online control phases.

## Safety / Guardrails / Governance
paths: src/mlsdm/security/, policies/, SAFETY_POLICY.yaml, tests/security/test_ai_safety_invariants.py
citations: [@bai2022_constitutional] [@gabriel2020_alignment] [@weidinger2023_veil]
rationale: Constitutional AI (Bai et al.) informs policy-grounded guardrails enforced by security modules and policy files. Alignment framing (Gabriel) and justice principles (Weidinger et al.) drive the invariants exercised in safety tests.

## Evidence / Metrics / Reproducibility
paths: docs/METRICS_SOURCE.md, reports/, scripts/validate_bibliography.py, tests/unit/test_metrics_evidence_paths.py
citations: [@openssf2023_slsa] [@torresarias2019_intoto] [@elkishky2022_sigstore]
rationale: Supply-chain provenance (SLSA) and in-toto attestations map to evidence capture and reporting paths. Sigstore signing guidance ensures reproducible, verifiable artifacts and is enforced via bibliography validation and metrics evidence tests.

## Observability (logging/metrics/tracing)
paths: src/mlsdm/observability/, deploy/grafana/, tests/observability/
citations: [@ieee2020_7010] [@nist2023_rmf] [@hbp2024_assessment]
rationale: IEEE 7010 well-being metrics and NIST RMF monitoring expectations guide logging, metrics, and tracing hooks across observability packages. System-scale assessments (Human Brain Project review) reinforce the need for dashboards and tests that surface operational impact.

## API / Entrypoints / CLI
paths: src/mlsdm/api/, src/mlsdm/entrypoints/, src/mlsdm/cli/
citations: [@openai2023_gpt4] [@touvron2023_llama2] [@ouyang2022_instruct]
rationale: Foundation model APIs (GPT-4, Llama 2) anchor the HTTP/CLI surfaces that wrap inference and control paths. Instruction-following alignment (Ouyang et al.) informs defaults and interface safeguards exposed through entrypoints.

## Evaluation (unit/integration/e2e/property/perf)
paths: tests/unit/, tests/integration/, tests/e2e/, tests/property/, benchmarks/
citations: [@wang2024_clllm] [@openai2023_gpt4] [@lewis2020_rag]
rationale: Continual-learning survey benchmarks (Wang et al.) motivate layered unit, integration, and property suites. The GPT-4 report and RAG evaluations document empirical baselines that our end-to-end and performance tests aim to reproduce and guard.
