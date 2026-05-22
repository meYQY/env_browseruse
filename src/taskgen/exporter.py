"""Stage 12: Export outputs in various formats."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _filter_quality_passed(tasks: list[dict]) -> list[dict]:
    return [t for t in tasks if t.get("quality_checks", {}).get("passed", True)]


def export_tasks_json(tasks: list[dict], path: Path) -> None:
    tasks = _filter_quality_passed(tasks)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")


def export_tasks_csv(tasks: list[dict], path: Path) -> None:
    tasks = _filter_quality_passed(tasks)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not tasks:
        return
    fieldnames = [
        "task_id", "task_description", "target_environment",
        "ability_dimension", "difficulty", "target_entity_id",
        "task_template", "structure_variant",
        "num_assertions", "verifier_executed",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for task in tasks:
            entity = task.get("target_entity", {})
            entity_id = entity.get("entity_id", "") if isinstance(entity, dict) else str(entity)
            structure = task.get("task_structure", {})
            gt = task.get("ground_truth", {})
            verifier = task.get("verifier", {})
            writer.writerow({
                "task_id": task.get("task_id", ""),
                "task_description": task.get("task_description", ""),
                "target_environment": task.get("target_environment", ""),
                "ability_dimension": task.get("ability_dimension", ""),
                "difficulty": task.get("difficulty", ""),
                "target_entity_id": entity_id,
                "task_template": structure.get("task_template", ""),
                "structure_variant": structure.get("structure_variant", ""),
                "num_assertions": len(gt.get("assertions", [])),
                "verifier_executed": verifier.get("execution_status", "not_executed"),
            })


def export_examples_markdown(tasks: list[dict], path: Path) -> None:
    tasks = _filter_quality_passed(tasks)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Generated Browser-Use Task Examples\n"]

    for i, task in enumerate(tasks, 1):
        entity = task.get("target_entity", {})
        entity_id = entity.get("entity_id", "") if isinstance(entity, dict) else str(entity)
        gt = task.get("ground_truth", {})
        verifier = task.get("verifier", {})
        validation = task.get("validation_status", {})

        lines.append(f"## Task {i}: {task.get('task_id', '')}\n")
        lines.append(f"**Task description:**\n{task.get('task_description', '')}\n")
        lines.append(f"**Target environment:** {task.get('target_environment', '')}\n")
        lines.append(f"**Ability dimension:** {task.get('ability_dimension', '')}\n")
        lines.append(f"**Difficulty:** {task.get('difficulty', '')}\n")
        lines.append(f"**Target entity:** {entity_id}\n")

        lines.append("**Ground truth:**\n")
        for assertion in gt.get("assertions", []):
            co = assertion.get("check_object", "")
            conds = assertion.get("conditions", {})
            satisfy = assertion.get("must_satisfy", {})
            lines.append(f"- `{co}` where {conds} must satisfy {satisfy}\n")

        lines.append("**Verifier:**\n")
        for check in verifier.get("checks", []):
            query = check.get("query", {})
            cond = check.get("condition", {})
            lines.append(f"- Query `{query.get('resource', '')}` with filters {query.get('filters', {})}, check {cond}\n")
        lines.append(f"- Execution status: `{verifier.get('execution_status', 'not_executed')}`\n")

        lines.append("**Validation status:**\n")
        lines.append(f"- symbolic_grounded: {validation.get('symbolic_grounded', False)}\n")
        lines.append(f"- backend_grounded: {validation.get('backend_grounded', False)}\n")
        lines.append(f"- verifier_executed: {validation.get('verifier_executed', False)}\n")
        lines.append(f"- needs_backend_validation: {validation.get('needs_backend_validation', True)}\n")
        lines.append("---\n")

    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_generation_report(
    tasks: list[dict],
    rejected: list[dict],
    diversity_stats: dict,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    rejection_reasons = {}
    for r in rejected:
        reason = r.get("rejection_reason", "unknown")
        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

    verifier_statuses = {}
    for task in tasks:
        v = task.get("verifier", {})
        status = v.get("execution_status", "not_executed")
        verifier_statuses[status] = verifier_statuses.get(status, 0) + 1

    report = {
        "total_generated": len(tasks),
        "total_rejected": len(rejected),
        "diversity": diversity_stats,
        "rejection_reasons": rejection_reasons,
        "verifier_execution_summary": verifier_statuses,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")
