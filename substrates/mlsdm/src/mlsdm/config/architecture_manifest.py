"""Architecture manifest defining module boundaries and contracts.

This manifest provides a single source of truth for module responsibilities,
public interfaces, and allowed dependencies. It is intentionally lightweight
to keep validation fast and to avoid introducing new runtime dependencies.

The manifest is validated in tests to ensure:
* Every declared module directory exists
* Public interface files are present
* Allowed dependencies only reference known modules
* Layers use a constrained vocabulary for consistency
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence  # noqa: TC003
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
KNOWN_LAYERS = {
    "interface",
    "service",
    "engine",
    "cognitive-core",
    "memory",
    "cross-cutting",
    "integration",
    "foundation",
}


@dataclass(frozen=True)
class ArchitectureModule:
    """Declarative description of a module boundary."""

    name: str
    path: str
    layer: str
    responsibilities: Sequence[str]
    public_interfaces: Sequence[str]
    allowed_dependencies: Sequence[str]

    def absolute_path(self) -> Path:
        """Absolute filesystem path to the module directory."""
        return PACKAGE_ROOT / self.path

    def interface_paths(self) -> tuple[Path, ...]:
        """Absolute filesystem paths to declared public interface files."""
        base = self.absolute_path()
        return tuple(base / interface for interface in self.public_interfaces)


ARCHITECTURE_MANIFEST: tuple[ArchitectureModule, ...] = (
    ArchitectureModule(
        name="api",
        path="api",
        layer="interface",
        responsibilities=(
            "FastAPI surface area",
            "request validation and middleware",
            "lifecycle hooks for the cognitive engine",
        ),
        public_interfaces=("app.py", "health.py", "schemas.py"),
        allowed_dependencies=(
            "engine",
            "core",
            "router",
            "security",
            "observability",
            "utils",
            "contracts",
        ),
    ),
    ArchitectureModule(
        name="sdk",
        path="sdk",
        layer="interface",
        responsibilities=(
            "client-facing SDK for embedding MLSDM",
            "configuration helpers for NeuroCognitiveEngine",
        ),
        public_interfaces=("neuro_engine_client.py",),
        allowed_dependencies=("engine", "utils"),
    ),
    ArchitectureModule(
        name="cli",
        path="cli",
        layer="interface",
        responsibilities=(
            "command-line entrypoints for local orchestration",
            "operator workflows for running or inspecting the engine",
        ),
        public_interfaces=("main.py", "__main__.py"),
        allowed_dependencies=("core", "config", "entrypoints", "utils"),
    ),
    ArchitectureModule(
        name="entrypoints",
        path="entrypoints",
        layer="interface",
        responsibilities=(
            "runtime entrypoints for serving and health checks",
            "environment bootstrap and process lifecycle glue",
        ),
        public_interfaces=("serve.py", "dev_entry.py", "cloud_entry.py", "agent_entry.py", "health.py"),
        allowed_dependencies=("api", "config", "core", "engine", "utils"),
    ),
    ArchitectureModule(
        name="service",
        path="service",
        layer="service",
        responsibilities=(
            "legacy service shims for canonical API hosting",
            "process-level glue for backwards-compatible integrations",
        ),
        public_interfaces=("neuro_engine_service.py",),
        allowed_dependencies=("api", "entrypoints", "utils"),
    ),
    ArchitectureModule(
        name="engine",
        path="engine",
        layer="engine",
        responsibilities=(
            "composition of cognitive subsystems",
            "engine configuration and factories",
            "routing to wrappers and adapters",
        ),
        public_interfaces=("neuro_cognitive_engine.py", "factory.py"),
        allowed_dependencies=(
            "core",
            "cognition",
            "router",
            "adapters",
            "security",
            "risk",
            "observability",
            "utils",
            "deploy",
            "config",
        ),
    ),
    ArchitectureModule(
        name="core",
        path="core",
        layer="cognitive-core",
        responsibilities=(
            "orchestration of cognitive pipeline",
            "decision loops and adaptation sequencing",
            "LLM wrapper coordination",
            "memory manager lifecycle and gating",
        ),
        public_interfaces=("cognitive_controller.py", "llm_pipeline.py", "memory_manager.py"),
        allowed_dependencies=(
            "config",
            "cognition",
            "memory",
            "rhythm",
            "speech",
            "extensions",
            "observability",
            "utils",
            "security",
            "risk",
            "protocols",
        ),
    ),
    ArchitectureModule(
        name="cognition",
        path="cognition",
        layer="cognitive-core",
        responsibilities=(
            "moral valuation and role-boundary decision loops",
            "risk-gating signals for policy-aware cognition",
            "semantic matching and adaptation heuristics",
        ),
        public_interfaces=(
            "__init__.py",
            "moral_filter.py",
            "moral_filter_v2.py",
            "role_boundary_controller.py",
            "ontology_matcher.py",
            "synergy_experience.py",
        ),
        allowed_dependencies=("config", "observability", "utils"),
    ),
    ArchitectureModule(
        name="rhythm",
        path="rhythm",
        layer="cognitive-core",
        responsibilities=(
            "wake/sleep rhythm control loop",
            "phase timing for decision and adaptation cadence",
        ),
        public_interfaces=("cognitive_rhythm.py",),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="neuro_ai",
        path="neuro_ai",
        layer="cognitive-core",
        responsibilities=(
            "prediction-error primitives and adaptation loops",
            "neuro-inspired contract registration for cognitive subsystems",
            "bridges between memory, rhythm, and cognition modules",
        ),
        public_interfaces=(
            "__init__.py",
            "contracts.py",
            "contract_api.py",
            "prediction_error.py",
            "adapters.py",
            "config.py",
        ),
        allowed_dependencies=("cognition", "config", "core", "memory", "rhythm", "utils", "protocols"),
    ),
    ArchitectureModule(
        name="speech",
        path="speech",
        layer="cognitive-core",
        responsibilities=(
            "speech-governance policy interfaces",
            "post-generation risk gating and correction loops",
        ),
        public_interfaces=("governance.py",),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="memory",
        path="memory",
        layer="memory",
        responsibilities=(
            "multi-level synaptic memory primitives",
            "phase-entangled lattice memory",
            "memory calibration and persistence",
        ),
        public_interfaces=("multi_level_memory.py", "phase_entangled_lattice_memory.py"),
        allowed_dependencies=("config", "observability", "security", "utils"),
    ),
    ArchitectureModule(
        name="state",
        path="state",
        layer="memory",
        responsibilities=(
            "system state schemas and migrations",
            "persistence contracts for long-lived runtime state",
        ),
        public_interfaces=("system_state_schema.py", "system_state_store.py", "system_state_migrations.py"),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="router",
        path="router",
        layer="service",
        responsibilities=(
            "policy-aware routing between LLM providers",
            "adapter selection and failover",
        ),
        public_interfaces=("llm_router.py",),
        allowed_dependencies=("adapters", "security", "observability", "utils"),
    ),
    ArchitectureModule(
        name="adapters",
        path="adapters",
        layer="integration",
        responsibilities=(
            "provider-specific adapters",
            "provider factory and safety shims",
        ),
        public_interfaces=("provider_factory.py", "llm_provider.py"),
        allowed_dependencies=("security", "utils"),
    ),
    ArchitectureModule(
        name="extensions",
        path="extensions",
        layer="integration",
        responsibilities=(
            "optional cognitive extensions (e.g., neuro-language components)",
            "sandboxed training hooks with risk gating",
        ),
        public_interfaces=("neuro_lang_extension.py",),
        allowed_dependencies=("config", "core", "observability", "speech", "utils"),
    ),
    ArchitectureModule(
        name="deploy",
        path="deploy",
        layer="service",
        responsibilities=(
            "canary rollout control loops",
            "risk-gated promotion and rollback logic",
        ),
        public_interfaces=("canary_manager.py",),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="risk",
        path="risk",
        layer="cross-cutting",
        responsibilities=(
            "threat-model gating and risk assessment fusion",
            "runtime mode switching and degradation orchestration",
            "emergency fallback directives for safe execution",
        ),
        public_interfaces=("__init__.py", "safety_control.py"),
        allowed_dependencies=("config", "security", "cognition", "observability", "contracts", "protocols", "utils"),
    ),
    ArchitectureModule(
        name="security",
        path="security",
        layer="cross-cutting",
        responsibilities=(
            "policy engine and guardrails",
            "payload scrubbing and RBAC helpers",
            "rate limiting primitives",
        ),
        public_interfaces=("policy_engine.py", "guardrails.py", "payload_scrubber.py"),
        allowed_dependencies=("utils", "observability"),
    ),
    ArchitectureModule(
        name="observability",
        path="observability",
        layer="cross-cutting",
        responsibilities=("metrics, logging, and tracing infrastructure",),
        public_interfaces=("logger.py", "metrics.py", "tracing.py"),
        allowed_dependencies=("utils",),
    ),
    ArchitectureModule(
        name="config",
        path="config",
        layer="foundation",
        responsibilities=(
            "configuration schemas and calibration defaults",
            "runtime mode and performance SLO definitions",
        ),
        public_interfaces=("__init__.py", "calibration.py", "runtime.py", "perf_slo.py", "env_compat.py"),
        allowed_dependencies=("policy",),
    ),
    ArchitectureModule(
        name="protocols",
        path="protocols",
        layer="foundation",
        responsibilities=(
            "protocol definitions for inter-module signal contracts",
            "lightweight typed interfaces for cognitive-core communication",
            "dependency inversion abstractions for contracts",
        ),
        public_interfaces=("__init__.py", "neuro_signals.py"),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="policy",
        path="policy",
        layer="foundation",
        responsibilities=(
            "policy contract loading and validation",
            "canonical policy data export for enforcement",
            "runtime policy bundle access for governance",
        ),
        public_interfaces=("__init__.py", "loader.py"),
        allowed_dependencies=(),
    ),
    ArchitectureModule(
        name="contracts",
        path="contracts",
        layer="foundation",
        responsibilities=(
            "typed contracts for engine inputs, outputs, and errors",
            "shared protocol models for API and governance",
        ),
        public_interfaces=("__init__.py", "engine_models.py", "speech_models.py", "errors.py", "neuro_signals.py"),
        allowed_dependencies=("protocols",),
    ),
    ArchitectureModule(
        name="utils",
        path="utils",
        layer="foundation",
        responsibilities=(
            "configuration loading and validation",
            "shared primitives (bulkheads, circuit breakers, caches)",
            "lightweight metrics helpers",
        ),
        public_interfaces=("config_loader.py", "config_validator.py", "metrics.py"),
        allowed_dependencies=("security",),
    ),
)


def validate_manifest(manifest: Iterable[ArchitectureModule]) -> list[str]:
    """Validate manifest consistency and return a list of issues."""
    modules = list(manifest)
    issues: list[str] = []

    names = [module.name for module in modules]
    if len(names) != len(set(names)):
        issues.append("Module names must be unique")

    for module in modules:
        if module.layer not in KNOWN_LAYERS:
            issues.append(f"Unknown layer '{module.layer}' for module '{module.name}'")

        module_path = module.absolute_path()
        if not module_path.exists():
            issues.append(f"Path does not exist for module '{module.name}': {module_path}")
        elif not module_path.is_dir():
            issues.append(f"Path for module '{module.name}' is not a directory: {module_path}")

        if not module.responsibilities:
            issues.append(f"No responsibilities defined for module '{module.name}'")
        if not module.public_interfaces:
            issues.append(f"No public interfaces defined for module '{module.name}'")

        for interface_path in module.interface_paths():
            if not interface_path.exists():
                issues.append(
                    f"Public interface '{interface_path.name}' missing for module '{module.name}'"
                )

        for dependency in module.allowed_dependencies:
            if dependency not in names:
                issues.append(
                    f"Module '{module.name}' declares unknown dependency '{dependency}'"
                )

    return issues
