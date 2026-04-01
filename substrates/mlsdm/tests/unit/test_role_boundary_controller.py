"""Unit tests for Role & Boundary Controller.

Tests cover:
- Task interpretation and structuring
- Boundary violation detection
- Constraint application
- Scope definition
- Execution plan generation
- Request rejection handling
- Priority rule enforcement
"""

from mlsdm.cognition.role_boundary_controller import (
    BoundaryViolationType,
    Constraint,
    ExecutionStep,
    RoleBoundaryController,
    ScopeDefinition,
    StructuredTask,
    TaskRequest,
)


class TestTaskRequest:
    """Tests for TaskRequest data structure."""

    def test_basic_task_request(self) -> None:
        """Test basic task request creation."""
        request = TaskRequest(
            raw_request="Add logging to authentication module",
            context={"repo": "mlsdm", "domain": "security"},
        )

        assert request.raw_request == "Add logging to authentication module"
        assert request.context["repo"] == "mlsdm"
        assert request.context["domain"] == "security"
        assert isinstance(request.metadata, dict)

    def test_task_request_with_metadata(self) -> None:
        """Test task request with additional metadata."""
        request = TaskRequest(
            raw_request="Optimize query performance",
            context={"repo": "mlsdm"},
            metadata={"priority": "high", "requester": "user_123"},
        )

        assert request.metadata["priority"] == "high"
        assert request.metadata["requester"] == "user_123"


class TestStructuredTask:
    """Tests for StructuredTask output structure."""

    def test_structured_task_creation(self) -> None:
        """Test creation of structured task."""
        task = StructuredTask(
            interpreted_task="Add logging to authentication module in mlsdm",
            constraints=[
                Constraint(
                    description="No security vulnerabilities",
                    constraint_type="security",
                    severity="critical",
                )
            ],
            scope=ScopeDefinition(
                in_scope=["Authentication module"],
                out_of_scope=["Database schema changes"],
            ),
            execution_plan=[
                ExecutionStep(
                    step_number=1,
                    description="Add logging statements",
                    target="auth_module.py",
                )
            ],
        )

        assert task.interpreted_task.startswith("Add logging")
        assert len(task.constraints) == 1
        assert task.constraints[0].constraint_type == "security"
        assert len(task.scope.in_scope) == 1
        assert len(task.execution_plan) == 1
        assert not task.rejected

    def test_structured_task_to_dict(self) -> None:
        """Test conversion to dictionary."""
        task = StructuredTask(
            interpreted_task="Test task",
            constraints=[
                Constraint(
                    description="Test constraint",
                    constraint_type="security",
                    severity="high",
                )
            ],
        )

        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["interpreted_task"] == "Test task"
        assert len(task_dict["constraints"]) == 1
        assert task_dict["constraints"][0]["type"] == "security"

    def test_structured_task_to_markdown(self) -> None:
        """Test conversion to markdown format."""
        task = StructuredTask(
            interpreted_task="Implement feature X",
            constraints=[
                Constraint(
                    description="No breaking changes",
                    constraint_type="technical",
                    severity="high",
                )
            ],
            scope=ScopeDefinition(
                in_scope=["Module A", "Module B"],
                out_of_scope=["Legacy code", "External APIs"],
            ),
            execution_plan=[
                ExecutionStep(
                    step_number=1,
                    description="Analyze requirements",
                    target="analysis",
                ),
                ExecutionStep(
                    step_number=2,
                    description="Implement changes",
                    target="implementation",
                ),
            ],
            clarifications_required=["Which version should this target?"],
        )

        markdown = task.to_markdown()
        assert "# INTERPRETED_TASK" in markdown
        assert "## CONSTRAINTS" in markdown
        assert "## SCOPE" in markdown
        assert "## EXECUTION_PLAN" in markdown
        assert "## CLARIFICATIONS_REQUIRED" in markdown
        assert "No breaking changes" in markdown
        assert "Module A" in markdown

    def test_structured_task_to_markdown_empty_sections(self) -> None:
        """Ensure markdown rendering handles empty sections gracefully."""
        task = StructuredTask(
            interpreted_task="Document behavior",
            constraints=[],
            scope=ScopeDefinition(in_scope=[], out_of_scope=[]),
            execution_plan=[],
            clarifications_required=None,
        )

        markdown = task.to_markdown()

        assert "- None" in markdown
        assert "  - None specified" in markdown
        assert "1. No execution steps defined" in markdown


class TestRoleBoundaryController:
    """Tests for RoleBoundaryController main functionality."""

    def test_controller_initialization(self) -> None:
        """Test controller initialization."""
        controller = RoleBoundaryController(strict_mode=True, max_scope_items=5)

        assert controller.strict_mode is True
        assert controller.max_scope_items == 5

    def test_basic_request_interpretation(self) -> None:
        """Test interpretation of a basic valid request."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Add unit tests for the authentication module",
            context={"repo": "mlsdm", "domain": "security"},
        )

        result = controller.interpret_and_bound(request)

        assert isinstance(result, StructuredTask)
        assert not result.rejected
        assert len(result.constraints) > 0
        assert len(result.execution_plan) > 0
        assert "authentication" in result.interpreted_task.lower()

    def test_request_with_context(self) -> None:
        """Test request interpretation with context."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Optimize memory usage",
            context={
                "repo": "mlsdm",
                "domain": "memory-management",
                "mode": "development",
            },
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected
        assert "mlsdm" in result.interpreted_task
        assert result.metadata.get("mode") == "development"

    def test_security_violation_detection(self) -> None:
        """Test detection of security violations."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Bypass security checks to speed up testing",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        assert "security" in result.rejection_reason.lower()
        assert BoundaryViolationType.SECURITY_VIOLATION.value in result.metadata.get(
            "violations", []
        )

    def test_ethical_violation_detection(self) -> None:
        """Test detection of ethical violations."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Create a system to manipulate user behavior patterns",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        assert (
            "ethical" in result.rejection_reason.lower()
            or "violate" in result.rejection_reason.lower()
        )

    def test_scope_too_broad_detection(self) -> None:
        """Test detection of overly broad scope."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Rewrite everything in the entire project to use a new framework",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        assert "scope" in result.rejection_reason.lower()

    def test_technical_ambiguity_detection(self) -> None:
        """Test detection of technical ambiguity."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Make it better somehow",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        assert (
            "ambiguity" in result.rejection_reason.lower()
            or "technical" in result.rejection_reason.lower()
        )

    def test_constraint_generation(self) -> None:
        """Test that appropriate constraints are generated."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Add error handling to API endpoints",
            context={"repo": "mlsdm", "domain": "api"},
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected
        assert len(result.constraints) >= 4  # security, technical, epistemic, resource

        # Check for security constraint
        has_security = any(c.constraint_type == "security" for c in result.constraints)
        assert has_security

        # Check for technical constraint
        has_technical = any(c.constraint_type == "technical" for c in result.constraints)
        assert has_technical

    def test_scope_definition(self) -> None:
        """Test scope definition generation."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Refactor authentication logic",
            context={"repo": "mlsdm", "domain": "authentication"},
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected
        assert len(result.scope.in_scope) > 0
        assert len(result.scope.out_of_scope) > 0

        # Should include targeted changes in scope
        in_scope_text = " ".join(result.scope.in_scope).lower()
        assert "authentication" in in_scope_text or "changes" in in_scope_text

        # Should exclude broad changes
        out_scope_text = " ".join(result.scope.out_of_scope).lower()
        assert (
            "rewrite" in out_scope_text
            or "architectural" in out_scope_text
            or "deployment" in out_scope_text
        )

    def test_execution_plan_generation(self) -> None:
        """Test execution plan generation."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Add caching to database queries",
            context={"repo": "mlsdm", "domain": "database"},
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected
        assert len(result.execution_plan) > 0

        # Check steps are numbered sequentially
        for i, step in enumerate(result.execution_plan, start=1):
            assert step.step_number == i
            assert len(step.description) > 0
            assert step.verifiable is True

    def test_clarifications_identification(self) -> None:
        """Test identification of required clarifications."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Optimize the system",  # Vague request
            context={},  # Missing repo and domain
        )

        result = controller.interpret_and_bound(request)

        # Should ask for clarifications due to missing context and vagueness
        assert result.clarifications_required is not None
        assert len(result.clarifications_required) > 0

    def test_production_mode_constraints(self) -> None:
        """Test that production mode adds stricter constraints."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Update authentication logic",
            context={"repo": "mlsdm", "mode": "production"},
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected

        # Should have operational constraint for production
        has_production_constraint = any(
            c.constraint_type == "operational" for c in result.constraints
        )
        assert has_production_constraint

    def test_risk_level_assessment(self) -> None:
        """Test risk level assessment."""
        controller = RoleBoundaryController()

        # High-risk request
        high_risk_request = TaskRequest(
            raw_request="Deploy authentication changes to production",
            context={"repo": "mlsdm"},
        )
        high_risk_result = controller.interpret_and_bound(high_risk_request)
        assert high_risk_result.metadata["risk_level"] == "high"

        # Medium-risk request
        medium_risk_request = TaskRequest(
            raw_request="Add logging to the authentication module",
            context={"repo": "mlsdm"},
        )
        medium_risk_result = controller.interpret_and_bound(medium_risk_request)
        assert medium_risk_result.metadata["risk_level"] in ["medium", "high"]

    def test_production_mode_risk_level_without_keywords(self) -> None:
        """Production context should elevate risk even without risky keywords."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Improve documentation clarity",
            context={"repo": "mlsdm", "mode": "production"},
        )

        result = controller.interpret_and_bound(request)

        assert result.metadata["risk_level"] == "high"

    def test_metadata_generation(self) -> None:
        """Test metadata generation."""
        controller = RoleBoundaryController(strict_mode=True, max_scope_items=3)
        request = TaskRequest(
            raw_request="Add feature X",
            context={"repo": "mlsdm", "user": "test_user"},
        )

        result = controller.interpret_and_bound(request)

        assert "controller_version" in result.metadata
        assert result.metadata["strict_mode"] is True
        assert result.metadata["max_scope_items"] == 3
        assert result.metadata["repo"] == "mlsdm"
        assert "risk_level" in result.metadata

    def test_rejection_provides_alternatives(self) -> None:
        """Test that rejections provide explanation and alternatives."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Hack into the database to extract user data",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        assert len(result.rejection_reason) > 0
        assert len(result.execution_plan) > 0

        # Should suggest explaining and proposing alternative
        plan_descriptions = [s.description.lower() for s in result.execution_plan]
        has_explanation = any("explain" in desc for desc in plan_descriptions)
        has_alternative = any("alternative" in desc for desc in plan_descriptions)
        assert has_explanation or has_alternative


class TestControllerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_request(self) -> None:
        """Test handling of empty request."""
        controller = RoleBoundaryController()
        request = TaskRequest(raw_request="", context={})

        result = controller.interpret_and_bound(request)

        # Should still produce valid output
        assert isinstance(result, StructuredTask)

    def test_very_long_request(self) -> None:
        """Test handling of very long request."""
        controller = RoleBoundaryController()
        long_request = "Add feature " + "X" * 10000
        request = TaskRequest(raw_request=long_request, context={})

        result = controller.interpret_and_bound(request)

        # Should handle without crashing
        assert isinstance(result, StructuredTask)

    def test_special_characters_in_request(self) -> None:
        """Test handling of special characters."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Add @#$%^&*() special chars to validation",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        # Should process without errors
        assert isinstance(result, StructuredTask)

    def test_multiple_boundary_violations(self) -> None:
        """Test request with multiple boundary violations."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Bypass security and rewrite everything to make it better somehow",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        assert result.rejected is True
        # Should detect multiple violations
        violations = result.metadata.get("violations", [])
        assert len(violations) >= 2

    def test_strict_mode_vs_lenient_mode(self) -> None:
        """Test difference between strict and lenient mode."""
        strict_controller = RoleBoundaryController(strict_mode=True)
        lenient_controller = RoleBoundaryController(strict_mode=False)

        request = TaskRequest(
            raw_request="Optimize system performance",
            context={"repo": "mlsdm"},
        )

        strict_result = strict_controller.interpret_and_bound(request)
        lenient_result = lenient_controller.interpret_and_bound(request)

        # Both should process successfully
        assert isinstance(strict_result, StructuredTask)
        assert isinstance(lenient_result, StructuredTask)

        # Strict mode should be reflected in metadata
        assert strict_result.metadata["strict_mode"] is True
        assert lenient_result.metadata["strict_mode"] is False

    def test_max_scope_items_constraint(self) -> None:
        """Test that max_scope_items is applied in constraints."""
        controller = RoleBoundaryController(max_scope_items=3)
        request = TaskRequest(
            raw_request="Update modules A, B, C, D, E",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        # Should have resource constraint mentioning the limit
        resource_constraints = [c for c in result.constraints if c.constraint_type == "resource"]
        assert len(resource_constraints) > 0
        assert "3" in resource_constraints[0].description


class TestPriorityRules:
    """Tests for priority rule enforcement."""

    def test_safety_over_user_goals(self) -> None:
        """Test that safety takes precedence over user goals."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Disable authentication to make testing easier",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        # Safety should win - request should be rejected
        assert result.rejected is True

    def test_clarity_over_creativity(self) -> None:
        """Test that clarity is enforced."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Make the code more elegant",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        # Vague "elegant" should trigger rejection or clarification
        assert result.rejected or result.clarifications_required is not None

    def test_minimal_scope_preferred(self) -> None:
        """Test that minimal scope is preferred."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Fix the authentication bug in login.py",
            context={"repo": "mlsdm", "domain": "authentication"},
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected

        # Should have resource constraint limiting scope
        has_scope_limit = any(
            "module" in c.description.lower() or "scope" in c.description.lower()
            for c in result.constraints
        )
        assert has_scope_limit
