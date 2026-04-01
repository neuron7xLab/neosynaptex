# Role & Boundary Controller v1.0

## Overview

The **Role & Boundary Controller** is a contour/boundary filter for multi-agent neuro-cognitive systems in MLSDM. It acts as an engineering filter that interprets raw requests, applies constraints, filters unwanted actions, and returns structured, safe, precise task specifications for lower-level agents.

## Purpose

The controller's job is **not to respond to requests directly**, but to:
- Interpret tasks
- Apply boundaries and constraints
- Filter undesirable actions
- Return **clean, safe, precise** request/action plans for downstream agents

## Core Principles

### 0. Identity & Goal
- The controller is a **contour engineering filter**, not a "magical assistant"
- Its sole purpose: **ensure any downstream agent receives a correct, safe, technically clear task** within system policies

### 1. Input → Output Contract

**Input:**
- Raw user or agent request (may be chaotic, emotional, mixed)
- Optional short context (repo, domain, operation mode)

**Output:**
- Structured task with:
  - Clear goal (1-3 sentences)
  - Hard constraints (security, resources, technical boundaries)
  - Scope definition (in-scope vs out-of-scope)
  - Step-by-step execution plan
  - Required clarifications (if any)

### 2. Boundary Constraints

The controller applies these global rules to **every** request:

#### Security and Ethics
- Blocks tasks leading to: physical harm, malicious software, privacy violations
- Marks violations as OUT-OF-SCOPE
- Does not propagate unsafe actions downstream

#### Technical Hygiene
- No vague formulations like "make it better"
- Each action must be:
  - Verifiable
  - Bounded by scope
  - Specific to an object (file, module, metric, test, pipeline)

#### Epistemic Honesty
- If request requires knowledge beyond system capabilities:
  - Mark as OUT-OF-SCOPE
  - Never fabricate "plausible" facts
- May explicitly indicate: "requires external engineer/human"

#### Resource Boundaries
- No tasks like "rewrite entire project"
- Always narrow scope to:
  - One module
  - One pipeline
  - One test group
  - One function/class

### 3. Priority Rules

When conflicts or ambiguities arise:

1. **Safety > User Goals**
2. **Clarity/Reproducibility > Creativity**
3. **Small Controlled Scope > Large Refactoring**
4. **Transparency of Constraints > "Magical" Execution**

If user requests too much simultaneously:
- Break task into clear sub-goals in EXECUTION_PLAN
- Mark part of requirements as OUT-OF-SCOPE

## Usage

### Basic Example

```python
from mlsdm.cognition.role_boundary_controller import (
    RoleBoundaryController,
    TaskRequest,
)

controller = RoleBoundaryController()

request = TaskRequest(
    raw_request="Add logging to the authentication module",
    context={
        "repo": "mlsdm",
        "domain": "security",
        "mode": "development",
    },
)

result = controller.interpret_and_bound(request)

if not result.rejected:
    print(f"Task: {result.interpreted_task}")
    print(f"Constraints: {len(result.constraints)}")
    print(f"Steps: {len(result.execution_plan)}")
else:
    print(f"Rejected: {result.rejection_reason}")
```

### Output Formats

#### Dictionary Format
```python
task_dict = result.to_dict()
# Returns structured dict with all components
```

#### Markdown Format
```python
markdown = result.to_markdown()
# Returns formatted markdown following specification
```

## Architecture

### Classes

#### `RoleBoundaryController`
Main controller class that orchestrates boundary checking.

**Parameters:**
- `strict_mode` (bool): Enable strict boundary enforcement (default: True)
- `max_scope_items` (int): Maximum scope items per task (default: 5)

**Methods:**
- `interpret_and_bound(request: TaskRequest) -> StructuredTask`

#### `TaskRequest`
Input request structure.

**Attributes:**
- `raw_request` (str): Raw user/agent request
- `context` (dict): Optional context (repo, domain, mode)
- `metadata` (dict): Additional metadata

#### `StructuredTask`
Output task structure.

**Attributes:**
- `interpreted_task` (str): Clear goal formulation
- `constraints` (list[Constraint]): Hard constraints
- `scope` (ScopeDefinition): In-scope and out-of-scope items
- `execution_plan` (list[ExecutionStep]): Sequential steps
- `clarifications_required` (list[str] | None): Questions needing answers
- `rejected` (bool): Whether task was rejected
- `rejection_reason` (str): Reason for rejection
- `metadata` (dict): Additional metadata

### Boundary Violation Types

- `SECURITY_VIOLATION`: Security-related violations
- `ETHICAL_VIOLATION`: Ethical boundary violations
- `SCOPE_TOO_BROAD`: Overly broad scope
- `TECHNICAL_AMBIGUITY`: Vague technical requirements
- `EPISTEMIC_OVERREACH`: Beyond system knowledge
- `RESOURCE_EXCESSIVE`: Excessive resource requirements
- `PRIVACY_VIOLATION`: Privacy-related violations

## Examples

See `examples/role_boundary_controller_demo.py` for comprehensive examples:

1. Valid request with clear scope
2. Security violation (bypassing auth)
3. Scope too broad (complete rewrite)
4. Technical ambiguity (vague request)
5. Production mode with stricter constraints
6. Markdown output format
7. Request requiring clarifications

Run the demo:
```bash
python examples/role_boundary_controller_demo.py
```

## Integration with MLSDM

The Role & Boundary Controller integrates seamlessly with MLSDM's existing security and policy infrastructure:

- Uses MLSDM's security patterns and conventions
- Compatible with existing `PolicyEngine` and `Guardrails`
- Follows MLSDM's cognitive architecture principles
- Can be used upstream of other cognitive components

## Testing

Comprehensive test suite in `tests/unit/test_role_boundary_controller.py`:
- 29 unit tests (100% passing)
- Coverage: interpretation, violations, constraints, scope, execution plans, edge cases

Run tests:
```bash
pytest tests/unit/test_role_boundary_controller.py -v
```

## Hard Rejection Cases

The controller **must** mark a task as unacceptable (no EXECUTION_PLAN) if:
- Request directly violates base security policies
- User attempts to bypass system constraints
- Task impossible without critical external data (keys, secrets)

In such cases, the controller:
1. Explains why request cannot be fulfilled
2. Proposes safe alternative (if one exists)
3. Marks all policy-violating actions as OUT-OF-SCOPE

## Design Philosophy

The Role & Boundary Controller embodies:
- **Defense in depth**: Multiple layers of constraint checking
- **Fail-safe defaults**: Reject when uncertain
- **Explicit is better than implicit**: All decisions are auditable
- **Least privilege**: Minimal scope by default
- **Transparency**: Clear reasoning for all decisions

## Future Enhancements

Potential future improvements:
- LLM-based semantic analysis of requests
- Configurable priority weights
- Custom violation pattern plugins
- Integration with external policy engines
- Multi-language support for requests
- Learning from accepted/rejected patterns

## References

This implementation follows the specification provided in the problem statement, adapting it for MLSDM's cognitive architecture and Python ecosystem.

## License

This module is part of MLSDM and is licensed under the MIT License.
