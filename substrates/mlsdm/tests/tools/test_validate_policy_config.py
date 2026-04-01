from pathlib import Path

import yaml

from mlsdm.policy.validation import PolicyValidator


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def security_policy_fixture(workflow_file: str) -> dict:
    return {
        "policy_contract_version": "1.1",
        "version": "1.0",
        "policy_name": "Security Baseline",
        "enforcement_level": "blocking",
        "updated_at": "2025-12-07",
        "owner": {"name": "Security"},
        "rationale": "Test policy fixture.",
        "controls": {
            "required_checks": [
                {"name": "security-check", "workflow_file": workflow_file, "fail_on_violation": True}
            ],
            "security_requirements": {
                "authentication": {
                    "api_key_required": True,
                    "api_key_env_var": "API_KEY",
                    "never_hardcode_secrets": True,
                    "secrets_in_env_only": True,
                },
                "input_validation": {
                    "llm_safety_gateway_required": True,
                    "llm_safety_module": "mlsdm.security.llm_safety",
                    "payload_scrubber_module": "mlsdm.security.payload_scrubber",
                    "validate_all_external_input": True,
                },
                "data_protection": {
                    "scrub_pii_from_logs": True,
                    "scrubber_implementation": "mlsdm.security.payload_scrubber",
                    "fields_always_scrubbed": ["password"],
                },
                "dependencies": {
                    "sbom_generation_on_release": True,
                    "security_advisory_checks": True,
                    "outdated_dependency_monitoring": True,
                },
            },
            "audit_requirements": {
                "security_audit_frequency_days": 90,
                "penetration_test_frequency_days": 180,
                "security_training_required": True,
                "incident_response_plan_required": True,
            },
            "integrations": {
                "github_required_checks": ["Policy Check"],
                "branch_protection": {
                    "require_pr_reviews": 1,
                    "require_status_checks": True,
                    "enforce_admins": True,
                    "required_status_checks": ["Policy Check"],
                },
            },
            "ci_workflow_policy": {
                "prohibited_permissions": ["write-all"],
                "first_party_action_owners": ["actions"],
                "prohibited_mutable_refs": ["@main"],
            },
        },
        "thresholds": {
            "vulnerability_thresholds": {
                "critical": {"max_allowed": 0, "response_time_hours": 24, "fix_timeline_days": 7},
                "high": {"max_allowed": 0, "response_time_hours": 48, "fix_timeline_days": 14},
                "medium": {"max_allowed": 0, "response_time_hours": 168, "fix_timeline_days": 30},
                "low": {"max_allowed": 5, "response_time_hours": 336, "fix_timeline_days": 90},
            },
            "coverage_gate_minimum_percent": 75,
        },
    }


def slo_policy_fixture() -> dict:
    return {
        "policy_contract_version": "1.1",
        "version": "1.0",
        "policy_name": "Observability SLOs",
        "enforcement_level": "advisory",
        "updated_at": "2025-12-07",
        "owner": {"name": "Observability"},
        "rationale": "Test policy fixture.",
        "controls": {
            "monitoring": {
                "metrics": {
                    "required_exporters": ["prometheus"],
                    "collection_interval_seconds": 10,
                    "retention_days": 30,
                    "key_metrics": [{"name": "metric", "type": "counter"}],
                }
            },
            "logging": {
                "structured_logging_required": True,
                "log_levels": {"production": "INFO", "development": "DEBUG"},
                "required_fields": ["timestamp"],
            },
            "alerting": {
                "alert_manager_required": True,
                "notification_channels": ["email"],
                "critical_alerts": [
                    {"name": "Alert", "condition": "always", "severity": "high"}
                ],
            },
            "testing": {
                "slo_tests": {
                    "run_frequency": "on_pr",
                    "timeout_seconds": 300,
                    "retry_on_flake": False,
                    "test_suites": [
                        {"name": "fast", "marker": "benchmark", "max_duration_seconds": 120}
                    ],
                },
                "memory_tests": {
                    "deterministic_seeding": True,
                    "noise_tolerance_mb": 5.0,
                    "sample_count_min": 1,
                    "warmup_iterations": 1,
                },
            },
            "documentation": {
                "slo_spec": "SLO_SPEC.md",
                "validation_protocol": "SLO_VALIDATION_PROTOCOL.md",
                "runbook": "RUNBOOK.md",
                "observability_guide": "OBSERVABILITY_GUIDE.md",
            },
        },
        "thresholds": {
            "slos": {
                "api_defaults": {
                    "p50_latency_ms": 50.0,
                    "p95_latency_ms": 150.0,
                    "p99_latency_ms": 250.0,
                    "max_error_rate_percent": 1.0,
                    "min_availability_percent": 99.0,
                },
                "api_endpoints": [],
                "system_resources": [],
                "cognitive_engine": [],
            },
            "runtime_defaults": {
                "latency": {
                    "api_p50_ms": 50.0,
                    "api_p95_ms": 150.0,
                    "api_p99_ms": 250.0,
                    "engine_total_p50_ms": 100.0,
                    "engine_total_p95_ms": 600.0,
                    "engine_preflight_p95_ms": 30.0,
                    "generation_p95_ms": 50.0,
                },
                "error_rate": {
                    "max_error_rate_percent": 1.0,
                    "min_availability_percent": 99.0,
                    "expected_rejection_rate_percent_min": 0.0,
                    "expected_rejection_rate_percent_max": 30.0,
                },
                "throughput": {"min_rps": 50.0, "max_queue_depth": 100, "min_concurrent_capacity": 10},
                "load_multipliers": {
                    "moderate_load_slo": 1.2,
                    "moderate_load_error": 1.5,
                    "readiness_check": 2.0,
                    "liveness_check": 2.0,
                },
            },
            "error_budgets": {
                "monthly": {
                    "availability_target": 99.9,
                    "error_budget_percent": 0.1,
                    "downtime_minutes_allowed": 43.2,
                },
                "burn_rate_thresholds": {"fast_burn": 14.4, "slow_burn": 1.0},
            },
        },
    }


def test_validate_policy_config_success(tmp_path: Path):
    repo_root = tmp_path
    policy_dir = repo_root / "policy"
    policy_dir.mkdir()

    workflows_dir = repo_root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "security.yml").write_text("", encoding="utf-8")

    security_policy = security_policy_fixture(".github/workflows/security.yml")
    slo_policy = slo_policy_fixture()

    write_yaml(policy_dir / "security-baseline.yaml", security_policy)
    write_yaml(policy_dir / "observability-slo.yaml", slo_policy)

    validator = PolicyValidator(repo_root, policy_dir, enforce_registry=False)

    assert validator.validate_all()


def test_validate_policy_config_missing_workflow(tmp_path: Path):
    repo_root = tmp_path
    policy_dir = repo_root / "policy"
    policy_dir.mkdir()

    security_policy = security_policy_fixture(".github/workflows/missing.yml")
    slo_policy = slo_policy_fixture()

    write_yaml(policy_dir / "security-baseline.yaml", security_policy)
    write_yaml(policy_dir / "observability-slo.yaml", slo_policy)

    validator = PolicyValidator(repo_root, policy_dir, enforce_registry=False)

    assert not validator.validate_all()
