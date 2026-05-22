"""Stage 9: Generate natural-language task instruction via LLM."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm.base import LLMProvider


def generate_instruction(
    task_spec: dict,
    entity_selection: dict,
    ground_truth: dict,
    provider: "LLMProvider",
) -> str:
    """Generate natural-language task description using LLM provider.

    The LLM only verbalizes the structured task. It does not generate
    ground truth or verifier logic.
    """
    llm_input = {
        "target_entity": task_spec.get("target_entity", ""),
        "target_entities": task_spec.get("target_entities", {}),
        "target_environment": task_spec.get("target_environment", ""),
        "ability_dimension": task_spec.get("ability_dimension", ""),
        "difficulty": task_spec.get("difficulty", ""),
        "locator": entity_selection.get("selected_locator_fields", {}),
        "entity_type": entity_selection.get("entity_type", ""),
        "actions": task_spec.get("actions", []),
        "requirements": task_spec.get("requirements", {}),
        "requirements_by_target": task_spec.get("requirements_by_target", {}),
    }
    return provider.generate_instruction(llm_input)


def check_ambiguity(
    task_description: str,
    task_spec: dict,
    provider: "LLMProvider",
) -> dict:
    """Use LLM to check if task description is clear and consistent."""
    return provider.judge_ambiguity(task_description, task_spec)
