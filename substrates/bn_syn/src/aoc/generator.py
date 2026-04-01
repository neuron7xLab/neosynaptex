from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import GeneratedArtifact, TaskContract
from .state import AOCState


class CandidateGenerator(Protocol):
    def generate(self, state: AOCState, contract: TaskContract, section_budget: int) -> GeneratedArtifact:
        ...


@dataclass(frozen=True)
class DeterministicMarkdownGenerator:
    def generate(self, state: AOCState, contract: TaskContract, section_budget: int) -> GeneratedArtifact:
        required_sections = list(contract.constraints["required_sections"])
        n_sections = max(1, min(len(required_sections), section_budget))
        selected = required_sections[:n_sections]

        lines = [f"# {contract.task_id}", "", f"Objective: {contract.objective}", ""]
        for idx, sec in enumerate(selected, start=1):
            lines.append(f"## {sec}")
            lines.append(f"Deterministic section {idx} for iteration {state.iteration}.")
            lines.append("")
        content = "\n".join(lines).strip() + "\n"
        return GeneratedArtifact(
            content=content,
            metadata={
                "generator_kind": contract.generator["kind"],
                "seed": int(contract.generator["deterministic_seed"]),
                "section_budget": n_sections,
            },
        )
