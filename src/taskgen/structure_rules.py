"""Stage 2: Select structure variant based on difficulty/capability rules."""
from __future__ import annotations

import random
from typing import Any


def select_structure_variant(
    cell: dict,
    structure_rules: dict[str, list[dict]],
    rng: random.Random | None = None,
) -> dict:
    """Select a compatible structure variant for a generation cell.

    structure_rules is keyed like "Memory_L3" -> list of variant dicts.
    """
    rng = rng or random.Random()
    key = f"{cell['ability_dimension']}_{cell['difficulty']}"
    variants = structure_rules.get(key, [])
    if not variants:
        raise ValueError(f"No structure variants defined for {key}")
    return rng.choice(variants)


def variant_allows_actions(variant: dict, num_actions: int) -> bool:
    return variant.get("actions_min", 1) <= num_actions <= variant.get("actions_max", 99)


def variant_allows_conditions(variant: dict, num_conditions: int) -> bool:
    return variant.get("min_locator_conditions", 0) <= num_conditions <= variant.get("max_locator_conditions", 99)
