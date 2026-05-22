"""Stage 3: Select compatible task template."""
from __future__ import annotations

import random
from typing import Any


def select_task_template(
    cell: dict,
    variant: dict,
    templates: dict[str, dict],
    diversity_state: dict | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Select a task template compatible with the generation cell and structure variant."""
    rng = rng or random.Random()
    ds = diversity_state or {}
    template_counts = ds.get("template_counts", {})

    candidates = []
    for tid, tmpl in templates.items():
        if tmpl["site"] != cell["target_environment"]:
            continue
        if cell["ability_dimension"] not in tmpl.get("compatible_abilities", []):
            continue
        ability_diff_map = tmpl.get("ability_difficulty_map", {})
        if ability_diff_map and cell["ability_dimension"] in ability_diff_map:
            if cell["difficulty"] not in ability_diff_map[cell["ability_dimension"]]:
                continue
        elif cell["difficulty"] not in tmpl.get("compatible_difficulties", []):
            continue
        allowed = cell.get("allowed_task_templates", [])
        if allowed and tid not in allowed:
            continue
        num_actions = len(tmpl.get("allowed_actions", []))
        if not (variant.get("actions_min", 1) <= num_actions <= variant.get("actions_max", 99)):
            continue
        if _estimated_assertions(tmpl) < variant.get("min_assertions", 1):
            continue
        if cell["ability_dimension"] == "Long-horizon" and cell["difficulty"] == "L5":
            if num_actions < 3 or _estimated_assertions(tmpl) < 3:
                continue
        candidates.append((tid, tmpl))

    if not candidates:
        raise ValueError(
            f"No compatible template for {cell['ability_dimension']} "
            f"{cell['difficulty']} / {cell['target_environment']}"
        )

    # Prefer less-used templates for diversity
    min_count = min(template_counts.get(tid, 0) for tid, _ in candidates)
    least_used = [(tid, t) for tid, t in candidates if template_counts.get(tid, 0) <= min_count + 2]
    if least_used:
        candidates = least_used

    tid, tmpl = rng.choice(candidates)
    result = dict(tmpl)
    result["template_id"] = tid
    return result


def _estimated_assertions(template: dict) -> int:
    actions = template.get("allowed_actions", [])
    explicit = len(template.get("ground_truth_rules", []))
    if not actions:
        return explicit

    # add_to_cart + update_quantity can produce a non-conflicting existence
    # check plus the final quantity check even when the YAML has one cart rule.
    if "add_to_cart" in actions and "update_quantity" in actions:
        explicit = max(explicit, 2)

    # Missing explicit action rules fall back to deterministic canonical rules.
    return max(explicit, len(actions))
