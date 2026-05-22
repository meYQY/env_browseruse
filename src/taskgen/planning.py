"""Stage 1: Build generation cells from generation plan."""
from __future__ import annotations
from typing import Any


def build_generation_cells(plan: dict) -> list[dict]:
    """Expand a generation plan into concrete generation cells."""
    cells = []
    distributions = plan.get("distributions", [])
    target_total = plan.get("target_total", 100)

    for dist in distributions:
        ability = dist["ability_dimension"]
        env = dist["target_environment"]
        env_count = dist.get("count", 0)
        difficulty_weights = dist.get("difficulty_weights", {})
        total_weight = sum(difficulty_weights.values()) or 1

        for diff, weight in difficulty_weights.items():
            count = max(1, round(env_count * weight / total_weight))
            cells.append({
                "ability_dimension": ability,
                "difficulty": diff,
                "target_environment": env,
                "target_count": count,
                "allowed_task_templates": dist.get("allowed_task_templates", []),
            })

    return cells


def build_curated_cells(plan: dict) -> list[dict]:
    """Build cells for the curated 10-example set."""
    curated = plan.get("curated_examples", {})
    cells = []
    for spec in curated.get("specs", []):
        cells.append({
            "ability_dimension": spec["ability_dimension"],
            "difficulty": spec["difficulty"],
            "target_environment": spec["target_environment"],
            "target_count": 1,
            "allowed_task_templates": spec.get("allowed_task_templates", []),
        })
    return cells
