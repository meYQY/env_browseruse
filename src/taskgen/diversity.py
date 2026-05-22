"""Stage 11: Diversity selection and quota enforcement."""
from __future__ import annotations
from typing import Any
from collections import Counter


def check_diversity(tasks: list[dict], plan: dict | None = None) -> dict:
    """Compute diversity statistics for a task set."""
    by_ability = Counter(t.get("ability_dimension", "") for t in tasks)
    by_difficulty = Counter(t.get("difficulty", "") for t in tasks)
    by_environment = Counter(t.get("target_environment", "") for t in tasks)
    by_template = Counter(t.get("task_structure", {}).get("task_template", "") for t in tasks)
    by_variant = Counter(t.get("task_structure", {}).get("structure_variant", "") for t in tasks)

    entity_counts = Counter(
        t.get("target_entity", {}).get("entity_id", "")
        if isinstance(t.get("target_entity"), dict)
        else t.get("target_entity", "")
        for t in tasks
    )

    return {
        "by_ability": dict(by_ability),
        "by_difficulty": dict(by_difficulty),
        "by_environment": dict(by_environment),
        "by_task_template": dict(by_template),
        "by_structure_variant": dict(by_variant),
        "entity_reuse_count": dict(entity_counts.most_common(20)),
        "total_tasks": len(tasks),
        "unique_entities": len(set(entity_counts.keys())),
        "unique_templates": len(set(by_template.keys())),
    }


def enforce_diversity(
    candidates: list[dict],
    target_count: int,
    max_entity_reuse: int = 3,
    max_template_ratio: float = 0.4,
) -> list[dict]:
    """Select tasks from candidates enforcing diversity constraints.

    Returns a list of selected tasks.
    """
    selected = []
    entity_counts: Counter = Counter()
    template_counts: Counter = Counter()
    entity_template_counts: Counter = Counter()

    for task in _round_robin_by_cell(candidates):
        entity_ids = _get_entity_ids(task)
        primary_entity_id = entity_ids[0] if entity_ids else ""
        template_id = task.get("task_structure", {}).get("task_template", "")

        key = (primary_entity_id, template_id)
        if entity_template_counts[key] >= 2:
            continue

        if any(entity_counts[entity_id] >= max_entity_reuse for entity_id in entity_ids):
            continue

        max_for_template = max(1, int(target_count * max_template_ratio))
        if template_counts[template_id] >= max_for_template:
            continue

        selected.append(task)
        for entity_id in entity_ids:
            entity_counts[entity_id] += 1
        template_counts[template_id] += 1
        entity_template_counts[key] += 1

        if len(selected) >= target_count:
            break

    return selected


def _round_robin_by_cell(candidates: list[dict]) -> list[dict]:
    """Interleave candidates by ability/difficulty/environment.

    The generation pipeline produces candidates in plan order. A plain first-N
    selection can starve later environments, especially for Long-horizon cells.
    This preserves deterministic order within each cell while rotating across
    cells for better coverage.
    """
    groups: dict[tuple[str, str, str], list[dict]] = {}
    group_order: list[tuple[str, str, str]] = []
    for task in candidates:
        key = (
            task.get("ability_dimension", ""),
            task.get("difficulty", ""),
            task.get("target_environment", ""),
        )
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(task)

    ordered: list[dict] = []
    while any(groups.values()):
        for key in group_order:
            if groups[key]:
                ordered.append(groups[key].pop(0))
    return ordered


def select_curated_examples(
    tasks: list[dict],
    count: int = 10,
) -> list[dict]:
    """Select a curated subset covering L1-L5, Memory/Long-horizon, multiple environments."""
    examples: list[dict] = []
    used_environments: set[str] = set()
    used_templates: set[str] = set()

    for target_diff in ["L1", "L2", "L3", "L4", "L5"]:
        for target_ability in ["Memory", "Long-horizon"]:
            if len(examples) >= count:
                break
            candidates = [
                t for t in tasks
                if t not in examples
                and t.get("difficulty") == target_diff
                and t.get("ability_dimension") == target_ability
            ]
            if not candidates:
                continue

            def _score(t: dict) -> int:
                s = 0
                env = t.get("target_environment", "")
                tmpl = t.get("task_structure", {}).get("task_template", "")
                if env not in used_environments:
                    s += 4
                if tmpl not in used_templates:
                    s += 2
                return s

            best = max(candidates, key=_score)
            examples.append(best)
            used_environments.add(best.get("target_environment", ""))
            used_templates.add(best.get("task_structure", {}).get("task_template", ""))

    for task in tasks:
        if len(examples) >= count:
            break
        if task not in examples:
            examples.append(task)

    return examples[:count]


def _get_entity_id(task: dict) -> str:
    ids = _get_entity_ids(task)
    return ids[0] if ids else ""


def _get_entity_ids(task: dict) -> list[str]:
    target_entities = task.get("target_entities", {})
    if isinstance(target_entities, dict) and target_entities:
        ids = []
        for value in target_entities.values():
            if isinstance(value, dict):
                ids.append(value.get("entity_id", ""))
            else:
                ids.append(str(value))
        return [i for i in ids if i]

    te = task.get("target_entity", "")
    if isinstance(te, dict):
        return [te.get("entity_id", "")]
    return [str(te)] if te else []
