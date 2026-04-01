"""Integration tests for Role & Boundary Controller with MLSDM components.

These tests demonstrate how the controller integrates with:
- Security policy engine
- Moral filtering
- Overall cognitive architecture
"""

from mlsdm.cognition.role_boundary_controller import (
    RoleBoundaryController,
    TaskRequest,
)


class TestControllerIntegration:
    """Integration tests for Role & Boundary Controller."""

    def test_controller_with_security_context(self) -> None:
        """Test controller with security-sensitive context."""
        controller = RoleBoundaryController()
        request = TaskRequest(
            raw_request="Update authentication configuration",
            context={
                "repo": "mlsdm",
                "domain": "security",
                "mode": "production",
                "user_role": "admin",
            },
        )

        result = controller.interpret_and_bound(request)

        # Should accept with high constraints
        assert not result.rejected
        assert result.metadata["risk_level"] == "high"

        # Should have operational constraint for production
        has_production_constraint = any(
            c.constraint_type == "operational" for c in result.constraints
        )
        assert has_production_constraint

    def test_controller_workflow_integration(self) -> None:
        """Test integration with typical workflow."""
        controller = RoleBoundaryController()

        # Step 1: User submits vague request
        vague_request = TaskRequest(
            raw_request="Improve the system",
            context={"repo": "mlsdm"},
        )
        vague_result = controller.interpret_and_bound(vague_request)

        # Should identify need for clarifications
        assert vague_result.clarifications_required is not None

        # Step 2: User submits clear request after clarification
        clear_request = TaskRequest(
            raw_request="Add caching to database query functions in user module",
            context={
                "repo": "mlsdm",
                "domain": "database",
                "mode": "development",
            },
        )
        clear_result = controller.interpret_and_bound(clear_request)

        # Should accept with clear execution plan
        assert not clear_result.rejected
        assert len(clear_result.execution_plan) > 0
        assert "database" in clear_result.interpreted_task.lower()

    def test_controller_multi_context_handling(self) -> None:
        """Test controller handling multiple context dimensions."""
        controller = RoleBoundaryController()

        request = TaskRequest(
            raw_request="Refactor memory management functions",
            context={
                "repo": "mlsdm",
                "domain": "memory",
                "mode": "development",
                "priority": "medium",
                "team": "core",
            },
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected
        # Context should be preserved in metadata
        assert result.metadata["repo"] == "mlsdm"
        assert result.metadata["domain"] == "memory"
        assert result.metadata["mode"] == "development"

    def test_controller_rejects_unsafe_with_context(self) -> None:
        """Test that controller rejects unsafe requests regardless of context."""
        controller = RoleBoundaryController()

        # Even with admin context, should reject unsafe request
        request = TaskRequest(
            raw_request="Disable all authentication for easier testing",
            context={
                "repo": "mlsdm",
                "user_role": "admin",
                "mode": "development",
            },
        )

        result = controller.interpret_and_bound(request)

        # Should reject despite admin role
        assert result.rejected is True
        assert "security" in result.rejection_reason.lower()

    def test_controller_generates_actionable_steps(self) -> None:
        """Test that execution plans are actionable and specific."""
        controller = RoleBoundaryController()

        request = TaskRequest(
            raw_request="Add rate limiting to API endpoints",
            context={
                "repo": "mlsdm",
                "domain": "api",
            },
        )

        result = controller.interpret_and_bound(request)

        assert not result.rejected

        # Each step should be verifiable
        for step in result.execution_plan:
            assert step.verifiable is True
            assert len(step.description) > 0
            assert step.step_number > 0

        # Should have reasonable number of steps (not too many, not too few)
        assert 2 <= len(result.execution_plan) <= 10

    def test_controller_scope_limits_respected(self) -> None:
        """Test that scope limits are enforced in constraints."""
        max_items = 3
        controller = RoleBoundaryController(max_scope_items=max_items)

        request = TaskRequest(
            raw_request="Update error handling",
            context={"repo": "mlsdm"},
        )

        result = controller.interpret_and_bound(request)

        # Should have resource constraint mentioning the limit
        resource_constraints = [c for c in result.constraints if c.constraint_type == "resource"]
        assert len(resource_constraints) > 0
        assert str(max_items) in resource_constraints[0].description

    def test_controller_output_formats_consistent(self) -> None:
        """Test that different output formats are consistent."""
        controller = RoleBoundaryController()

        request = TaskRequest(
            raw_request="Add logging to user service",
            context={"repo": "mlsdm", "domain": "logging"},
        )

        result = controller.interpret_and_bound(request)

        # Get both formats
        dict_output = result.to_dict()
        markdown_output = result.to_markdown()

        # Both should contain key information
        assert result.interpreted_task in markdown_output
        assert dict_output["interpreted_task"] == result.interpreted_task

        # Markdown should have expected sections
        assert "# INTERPRETED_TASK" in markdown_output
        assert "## CONSTRAINTS" in markdown_output
        assert "## SCOPE" in markdown_output
        assert "## EXECUTION_PLAN" in markdown_output

    def test_controller_handles_edge_case_inputs(self) -> None:
        """Test controller robustness with edge case inputs."""
        controller = RoleBoundaryController()

        # Empty context
        result1 = controller.interpret_and_bound(
            TaskRequest(raw_request="Fix bug in module X", context={})
        )
        assert isinstance(result1.interpreted_task, str)

        # Very minimal request
        result2 = controller.interpret_and_bound(
            TaskRequest(raw_request="Fix", context={"repo": "mlsdm"})
        )
        assert isinstance(result2.interpreted_task, str)

        # Request with special characters
        result3 = controller.interpret_and_bound(
            TaskRequest(
                raw_request="Add @decorator to function_name()",
                context={"repo": "mlsdm"},
            )
        )
        assert isinstance(result3.interpreted_task, str)
