from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_instruction(self, structured_task: dict) -> str:
        """Generate natural-language task instruction from structured task spec."""

    @abstractmethod
    def judge_ambiguity(self, task_description: str, structured_task: dict) -> dict:
        """Check if task description is clear and consistent with structured spec.
        Returns {"clear": bool, "issues": list[str]}"""
