"""Role & Boundary Controller v1.0 for MLSDM.

This module provides a Role & Boundary Controller that acts as a contour/boundary
filter for multi-agent neuro-cognitive systems. It interprets raw requests, applies
constraints, filters unwanted actions, and returns clean, safe, precise task
specifications for lower-level agents.

The controller enforces:
- Security and ethics boundaries
- Technical hygiene and clarity
- Epistemic honesty (knowledge limitations)
- Resource constraints and scope control

Design Principles:
-----------------
- The controller does not execute tasks directly
- It transforms raw requests into structured, bounded task specifications
- All decisions are explicit and auditable
- Safety and clarity take precedence over feature requests

Example:
    >>> from mlsdm.cognition.role_boundary_controller import (
    ...     RoleBoundaryController,
    ...     TaskRequest,
    ... )
    >>>
    >>> controller = RoleBoundaryController()
    >>> request = TaskRequest(
    ...     raw_request="Make the system better",
    ...     context={"repo": "mlsdm", "domain": "cognitive-architecture"},
    ... )
    >>> structured_task = controller.interpret_and_bound(request)
    >>> print(structured_task.interpreted_task)
    >>> print(structured_task.constraints)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BoundaryViolationType(str, Enum):
    """Types of boundary violations that can occur."""

    SECURITY_VIOLATION = "security_violation"
    ETHICAL_VIOLATION = "ethical_violation"
    SCOPE_TOO_BROAD = "scope_too_broad"
    TECHNICAL_AMBIGUITY = "technical_ambiguity"
    EPISTEMIC_OVERREACH = "epistemic_overreach"
    RESOURCE_EXCESSIVE = "resource_excessive"
    PRIVACY_VIOLATION = "privacy_violation"


class TaskPriority(str, Enum):
    """Priority levels for decision conflicts.

    Note: These priorities are currently documented for reference and enforced
    implicitly in the controller logic. Future versions may use these explicitly
    for configurable priority-based decision making.
    """

    SAFETY = "safety"  # Highest priority
    CLARITY = "clarity"
    MINIMAL_SCOPE = "minimal_scope"
    TRANSPARENCY = "transparency"


@dataclass
class TaskRequest:
    """Input request to the Role & Boundary Controller.

    Attributes:
        raw_request: Raw user or agent request (may be chaotic, emotional, mixed)
        context: Optional short context (repo, domain, operation mode)
        metadata: Additional metadata for request processing
    """

    raw_request: str
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    """A single constraint to be enforced.

    Attributes:
        description: Description of the constraint
        constraint_type: Type of constraint (security, resource, technical, etc.)
        severity: How critical this constraint is (critical, high, medium, low)
    """

    description: str
    constraint_type: str = "general"
    severity: str = "medium"


@dataclass
class ScopeDefinition:
    """Defines what is in-scope and out-of-scope for a task.

    Attributes:
        in_scope: List of allowed/required actions
        out_of_scope: List of forbidden actions or deferred items
    """

    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)


@dataclass
class ExecutionStep:
    """A single step in the execution plan.

    Attributes:
        step_number: Sequential step number
        description: What the agent should do
        target: Specific target (file, module, metric, test, pipeline)
        verifiable: Whether this step can be verified/tested
    """

    step_number: int
    description: str
    target: str = ""
    verifiable: bool = True


@dataclass
class StructuredTask:
    """Output structure from Role & Boundary Controller.

    This is the clean, bounded task specification that agents receive.

    Attributes:
        interpreted_task: Clear goal formulation (1-3 sentences)
        constraints: List of hard constraints (security, policies, technical, resource)
        scope: What is in-scope vs out-of-scope
        execution_plan: Sequential steps for the agent to follow
        clarifications_required: Questions that need answers (or None)
        rejected: Whether the task was rejected due to policy violations
        rejection_reason: Reason for rejection if rejected=True
        metadata: Additional metadata (priority, risk_level, etc.)
    """

    interpreted_task: str
    constraints: list[Constraint] = field(default_factory=list)
    scope: ScopeDefinition = field(default_factory=ScopeDefinition)
    execution_plan: list[ExecutionStep] = field(default_factory=list)
    clarifications_required: list[str] | None = None
    rejected: bool = False
    rejection_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "interpreted_task": self.interpreted_task,
            "constraints": [
                {
                    "description": c.description,
                    "type": c.constraint_type,
                    "severity": c.severity,
                }
                for c in self.constraints
            ],
            "scope": {
                "in_scope": self.scope.in_scope,
                "out_of_scope": self.scope.out_of_scope,
            },
            "execution_plan": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "target": s.target,
                    "verifiable": s.verifiable,
                }
                for s in self.execution_plan
            ],
            "clarifications_required": self.clarifications_required,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Convert to markdown representation following the specified format."""
        lines = ["# INTERPRETED_TASK"]
        lines.append(self.interpreted_task)
        lines.append("")

        lines.append("## CONSTRAINTS")
        if self.constraints:
            for constraint in self.constraints:
                lines.append(f"- {constraint.description}")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## SCOPE")
        lines.append("- IN-SCOPE:")
        if self.scope.in_scope:
            for item in self.scope.in_scope:
                lines.append(f"  - {item}")
        else:
            lines.append("  - None specified")
        lines.append("- OUT-OF-SCOPE:")
        if self.scope.out_of_scope:
            for item in self.scope.out_of_scope:
                lines.append(f"  - {item}")
        else:
            lines.append("  - None specified")
        lines.append("")

        lines.append("## EXECUTION_PLAN")
        if self.execution_plan:
            for step in self.execution_plan:
                target_info = f" (target: {step.target})" if step.target else ""
                lines.append(f"{step.step_number}. {step.description}{target_info}")
        else:
            lines.append("1. No execution steps defined")
        lines.append("")

        lines.append("## CLARIFICATIONS_REQUIRED")
        if self.clarifications_required:
            for clarification in self.clarifications_required:
                lines.append(f"- {clarification}")
        else:
            lines.append("- None")

        return "\n".join(lines)


class RoleBoundaryController:
    """Role & Boundary Controller for multi-agent systems.

    This controller acts as a contour/boundary filter that:
    1. Interprets raw requests into clear task specifications
    2. Applies security, ethical, and technical constraints
    3. Filters unwanted actions
    4. Returns structured, safe, precise tasks for agents

    Priority Rules (for conflicts):
    1. Safety > User Goals
    2. Clarity/Reproducibility > Creativity
    3. Minimal Scope > Large Refactoring
    4. Transparency of Constraints > "Magical" Execution

    Attributes:
        strict_mode: If True, applies stricter boundary checks
        max_scope_items: Maximum number of items in a single task scope
    """

    def __init__(
        self,
        strict_mode: bool = True,
        max_scope_items: int = 5,
    ) -> None:
        """Initialize Role & Boundary Controller.

        Args:
            strict_mode: Enable strict boundary enforcement
            max_scope_items: Maximum scope items (files, modules, etc.) per task
        """
        self.strict_mode = strict_mode
        self.max_scope_items = max_scope_items
        self._violation_patterns = self._init_violation_patterns()

    def _init_violation_patterns(self) -> dict[BoundaryViolationType, list[str]]:
        """Initialize patterns for detecting boundary violations."""
        return {
            BoundaryViolationType.SECURITY_VIOLATION: [
                "hack",
                "exploit",
                "bypass security",
                "disable safety",
                "disable authentication",
                "disable all authentication",
                "remove authentication",
                "expose secrets",
                "credentials",
                "bypass",
            ],
            BoundaryViolationType.ETHICAL_VIOLATION: [
                "harm",
                "manipulate",
                "deceive",
                "discrimination",
                "violence",
                "drug",
                "weapon",
            ],
            BoundaryViolationType.SCOPE_TOO_BROAD: [
                "entire project",
                "rewrite everything",
                "all files",
                "complete refactor",
                "massive change",
            ],
            BoundaryViolationType.TECHNICAL_AMBIGUITY: [
                "make it better",
                "optimize somehow",
                "improve things",
                "fix everything",
                "more elegant",
                "better code",
                "cleaner",
            ],
        }

    def interpret_and_bound(self, request: TaskRequest) -> StructuredTask:
        """Main entry point: interpret request and apply boundaries.

        This method orchestrates the entire boundary control process:
        1. Analyze request for violations
        2. If violations found, reject with clear reason
        3. Otherwise, interpret into structured task with constraints
        4. Apply scope limitations
        5. Generate execution plan
        6. Identify clarifications needed

        Args:
            request: Input task request to process

        Returns:
            StructuredTask with bounded, safe specification

        Example:
            >>> controller = RoleBoundaryController()
            >>> request = TaskRequest(
            ...     raw_request="Add logging to the authentication module",
            ...     context={"repo": "mlsdm", "mode": "development"},
            ... )
            >>> task = controller.interpret_and_bound(request)
            >>> assert not task.rejected
            >>> assert len(task.execution_plan) > 0
        """
        # Step 1: Check for hard violations
        violations = self._detect_violations(request)

        if violations:
            return self._create_rejection(request, violations)

        # Step 2: Interpret the task
        interpreted_task = self._interpret_task(request)

        # Step 3: Apply constraints
        constraints = self._apply_constraints(request)

        # Step 4: Define scope
        scope = self._define_scope(request)

        # Step 5: Generate execution plan
        execution_plan = self._generate_execution_plan(request, scope)

        # Step 6: Identify clarifications
        clarifications = self._identify_clarifications(request)

        # Step 7: Build metadata
        metadata = self._build_metadata(request)

        structured_task = StructuredTask(
            interpreted_task=interpreted_task,
            constraints=constraints,
            scope=scope,
            execution_plan=execution_plan,
            clarifications_required=clarifications,
            rejected=False,
            metadata=metadata,
        )

        logger.info(
            "Task interpreted successfully",
            extra={
                "task": interpreted_task[:100],
                "num_constraints": len(constraints),
                "num_steps": len(execution_plan),
            },
        )

        return structured_task

    def _detect_violations(self, request: TaskRequest) -> list[BoundaryViolationType]:
        """Detect boundary violations in the request.

        Args:
            request: Task request to analyze

        Returns:
            List of detected violations (empty if none)
        """
        violations = []
        request_lower = request.raw_request.lower()

        for violation_type, patterns in self._violation_patterns.items():
            for pattern in patterns:
                if pattern.lower() in request_lower:
                    violations.append(violation_type)
                    break

        return violations

    def _create_rejection(
        self,
        request: TaskRequest,
        violations: list[BoundaryViolationType],
    ) -> StructuredTask:
        """Create a rejection response for violated requests.

        Args:
            request: Original request
            violations: List of detected violations

        Returns:
            StructuredTask with rejected=True
        """
        violation_descriptions = [v.value for v in violations]
        rejection_reason = (
            f"Request violates boundary policies: {', '.join(violation_descriptions)}. "
            "This request cannot be safely transformed into a task."
        )

        constraints = [
            Constraint(
                description="Security/confidentiality policy blocks this request",
                constraint_type="security",
                severity="critical",
            )
        ]

        scope = ScopeDefinition(
            in_scope=["Provide user explanation/alternative"],
            out_of_scope=["Any actions that violate policy"],
        )

        execution_plan = [
            ExecutionStep(
                step_number=1,
                description="Explain why request cannot be fulfilled",
                target="user_communication",
            ),
            ExecutionStep(
                step_number=2,
                description="Propose safe alternative (if exists)",
                target="user_communication",
            ),
        ]

        return StructuredTask(
            interpreted_task="Request cannot be safely processed",
            constraints=constraints,
            scope=scope,
            execution_plan=execution_plan,
            clarifications_required=None,
            rejected=True,
            rejection_reason=rejection_reason,
            metadata={
                "violations": violation_descriptions,
                "original_request": request.raw_request[:200],
            },
        )

    def _interpret_task(self, request: TaskRequest) -> str:
        """Interpret raw request into clear task description.

        Args:
            request: Task request

        Returns:
            Clear task description (1-3 sentences)
        """
        # This is a simplified interpretation - in production would use NLP/LLM
        # For now, we clean up and make more precise
        raw = request.raw_request.strip()

        # Add context if available
        context_parts = []
        if "repo" in request.context:
            context_parts.append(f"in repository '{request.context['repo']}'")
        if "domain" in request.context:
            context_parts.append(f"for {request.context['domain']}")

        context_str = " " + " ".join(context_parts) if context_parts else ""

        # For MVP, return cleaned request with context
        interpreted = f"{raw}{context_str}".strip()

        return interpreted

    def _apply_constraints(self, request: TaskRequest) -> list[Constraint]:
        """Apply boundary constraints to the task.

        Args:
            request: Task request

        Returns:
            List of constraints to enforce
        """
        constraints = []

        # Security constraints
        constraints.append(
            Constraint(
                description="No security vulnerabilities or credential exposure",
                constraint_type="security",
                severity="critical",
            )
        )

        # Technical hygiene constraints
        constraints.append(
            Constraint(
                description="All actions must be specific, verifiable, and bounded by scope",
                constraint_type="technical",
                severity="high",
            )
        )

        # Epistemic constraints
        constraints.append(
            Constraint(
                description="Do not fabricate facts outside system knowledge",
                constraint_type="epistemic",
                severity="high",
            )
        )

        # Resource constraints
        constraints.append(
            Constraint(
                description=f"Limit changes to maximum {self.max_scope_items} "
                f"modules/files/components",
                constraint_type="resource",
                severity="medium",
            )
        )

        # Add mode-specific constraints
        if request.context.get("mode") == "production":
            constraints.append(
                Constraint(
                    description="Production mode: Minimal changes, extensive testing required",
                    constraint_type="operational",
                    severity="high",
                )
            )

        return constraints

    def _define_scope(self, request: TaskRequest) -> ScopeDefinition:
        """Define what is in-scope vs out-of-scope.

        Args:
            request: Task request

        Returns:
            ScopeDefinition with boundaries
        """
        # This is simplified - would use more sophisticated parsing
        in_scope = []
        out_of_scope = []

        # Extract domain/module hints from context
        if "domain" in request.context:
            domain = request.context["domain"]
            in_scope.append(f"Changes to {domain} module")

        # Generic scope items
        in_scope.extend(
            [
                "Targeted changes to specified components",
                "Unit tests for modified code",
                "Documentation updates for changed interfaces",
            ]
        )

        out_of_scope.extend(
            [
                "Complete rewrites or architectural changes",
                "Changes to unrelated modules",
                "Production deployment (requires separate review)",
                "External service integrations without approval",
            ]
        )

        return ScopeDefinition(in_scope=in_scope, out_of_scope=out_of_scope)

    def _generate_execution_plan(
        self,
        request: TaskRequest,
        scope: ScopeDefinition,
    ) -> list[ExecutionStep]:
        """Generate concrete execution plan.

        Args:
            request: Task request
            scope: Defined scope

        Returns:
            List of execution steps
        """
        # Simplified execution plan generation
        steps = [
            ExecutionStep(
                step_number=1,
                description="Analyze existing code and identify target components",
                target="analysis_phase",
                verifiable=True,
            ),
            ExecutionStep(
                step_number=2,
                description="Implement changes following defined scope and constraints",
                target="implementation_phase",
                verifiable=True,
            ),
            ExecutionStep(
                step_number=3,
                description="Add or update tests to verify changes",
                target="testing_phase",
                verifiable=True,
            ),
            ExecutionStep(
                step_number=4,
                description="Update documentation to reflect changes",
                target="documentation_phase",
                verifiable=True,
            ),
        ]

        return steps

    def _identify_clarifications(self, request: TaskRequest) -> list[str] | None:
        """Identify required clarifications.

        Args:
            request: Task request

        Returns:
            List of questions or None if no clarifications needed
        """
        clarifications = []

        # Check for ambiguities
        if not request.context.get("repo"):
            clarifications.append("Which repository should this be applied to?")

        if not request.context.get("domain"):
            # Check if request is vague
            vague_terms = ["better", "improve", "optimize", "enhance"]
            if any(term in request.raw_request.lower() for term in vague_terms):
                clarifications.append(
                    "Please specify concrete metrics or requirements "
                    "for the improvement/optimization"
                )

        return clarifications if clarifications else None

    def _build_metadata(self, request: TaskRequest) -> dict[str, Any]:
        """Build metadata for the structured task.

        Args:
            request: Task request

        Returns:
            Metadata dictionary
        """
        metadata = {
            "controller_version": "1.0",
            "strict_mode": self.strict_mode,
            "max_scope_items": self.max_scope_items,
        }

        # Add request context
        metadata.update(request.context)

        # Add risk assessment
        metadata["risk_level"] = self._assess_risk_level(request)

        return metadata

    def _assess_risk_level(self, request: TaskRequest) -> str:
        """Assess risk level of the request.

        Args:
            request: Task request

        Returns:
            Risk level: low, medium, high, critical
        """
        request_lower = request.raw_request.lower()

        # High-risk keywords
        high_risk_keywords = [
            "production",
            "deploy",
            "delete",
            "remove",
            "database",
            "authentication",
            "security",
            "credential",
        ]

        if any(keyword in request_lower for keyword in high_risk_keywords):
            return "high"

        # Medium risk by default for code changes
        if request.context.get("mode") == "production":
            return "high"

        return "medium"
