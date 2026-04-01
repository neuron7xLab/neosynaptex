#!/usr/bin/env python3
"""Example usage of the Role & Boundary Controller.

This script demonstrates how to use the RoleBoundaryController to interpret
raw user requests and transform them into structured, bounded tasks with
clear constraints and execution plans.
"""

from mlsdm.cognition.role_boundary_controller import (
    RoleBoundaryController,
    TaskRequest,
)


def print_separator() -> None:
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def example_valid_request() -> None:
    """Example 1: Valid request with clear scope."""
    print("EXAMPLE 1: Valid Request - Add Logging")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Add structured logging to the authentication module",
        context={
            "repo": "mlsdm",
            "domain": "security",
            "mode": "development",
        },
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")
    print("\nInterpreted Task:")
    print(f"  {result.interpreted_task}")
    print(f"\nConstraints ({len(result.constraints)}):")
    for constraint in result.constraints[:3]:  # Show first 3
        print(f"  - [{constraint.severity.upper()}] {constraint.description}")
    print(f"\nExecution Plan ({len(result.execution_plan)} steps):")
    for step in result.execution_plan[:3]:  # Show first 3
        print(f"  {step.step_number}. {step.description}")
    print(f"\nRisk Level: {result.metadata.get('risk_level', 'unknown').upper()}")


def example_security_violation() -> None:
    """Example 2: Request with security violation."""
    print("EXAMPLE 2: Security Violation - Bypassing Security")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Bypass security checks to speed up the testing process",
        context={"repo": "mlsdm"},
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")

    if result.rejected:
        print("\nRejection Reason:")
        print(f"  {result.rejection_reason}")
        print("\nViolations Detected:")
        for violation in result.metadata.get("violations", []):
            print(f"  - {violation}")
        print("\nAlternative Actions:")
        for step in result.execution_plan:
            print(f"  {step.step_number}. {step.description}")


def example_scope_too_broad() -> None:
    """Example 3: Request with overly broad scope."""
    print("EXAMPLE 3: Scope Too Broad - Complete Rewrite")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Rewrite everything in the entire project to use microservices",
        context={"repo": "mlsdm"},
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")

    if result.rejected:
        print("\nRejection Reason:")
        print(f"  {result.rejection_reason}")


def example_technical_ambiguity() -> None:
    """Example 4: Request with technical ambiguity."""
    print("EXAMPLE 4: Technical Ambiguity - Vague Request")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Make the code more elegant and better",
        context={"repo": "mlsdm"},
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")

    if result.rejected:
        print("\nRejection Reason:")
        print(f"  {result.rejection_reason}")


def example_production_mode() -> None:
    """Example 5: Production mode with stricter constraints."""
    print("EXAMPLE 5: Production Mode - Stricter Constraints")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Update the rate limiting configuration",
        context={
            "repo": "mlsdm",
            "domain": "security",
            "mode": "production",
        },
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")
    print("\nInterpreted Task:")
    print(f"  {result.interpreted_task}")
    print("\nProduction Mode Constraints:")
    for constraint in result.constraints:
        if constraint.constraint_type == "operational":
            print(f"  - [{constraint.severity.upper()}] {constraint.description}")
    print(f"\nRisk Level: {result.metadata.get('risk_level', 'unknown').upper()}")


def example_markdown_output() -> None:
    """Example 6: Markdown format output."""
    print("EXAMPLE 6: Markdown Output Format")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Implement caching for database queries in the user service",
        context={
            "repo": "mlsdm",
            "domain": "database",
        },
    )

    result = controller.interpret_and_bound(request)

    print("Markdown Output:\n")
    print(result.to_markdown())


def example_with_clarifications() -> None:
    """Example 7: Request requiring clarifications."""
    print("EXAMPLE 7: Request Requiring Clarifications")
    print_separator()

    controller = RoleBoundaryController()
    request = TaskRequest(
        raw_request="Optimize the system performance",
        context={},  # Missing context
    )

    result = controller.interpret_and_bound(request)

    print("INPUT REQUEST:")
    print(f"  {request.raw_request}")
    print(f"\nRESULT: {'✓ ACCEPTED' if not result.rejected else '✗ REJECTED'}")

    if result.clarifications_required:
        print("\nClarifications Required:")
        for clarification in result.clarifications_required:
            print(f"  ? {clarification}")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 80)
    print(" Role & Boundary Controller - Usage Examples")
    print("=" * 80)

    example_valid_request()
    example_security_violation()
    example_scope_too_broad()
    example_technical_ambiguity()
    example_production_mode()
    example_markdown_output()
    example_with_clarifications()

    print("\n" + "=" * 80)
    print(" All Examples Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
