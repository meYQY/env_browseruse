"""Lightweight validator for generated symbolic browser-use tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "task_id",
    "task_description",
    "target_environment",
    "ability_dimension",
    "difficulty",
    "target_entity_ref",
    "task_family",
    "expected_answer_or_verification",
    "ground_truth",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_task(task: dict) -> list[str]:
    errors = []
    missing = sorted(REQUIRED_FIELDS - task.keys())
    if missing:
        errors.append(f"missing fields: {missing}")
    gt = task.get("ground_truth", {})
    if gt.get("grounding_status") != "symbolic_grounded":
        errors.append("ground_truth.grounding_status should be symbolic_grounded")
    if not gt.get("assertions"):
        errors.append("ground_truth.assertions must be non-empty")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, default=Path("outputs/sample_10_tasks.json"))
    args = parser.parse_args()
    tasks = load_json(args.path)
    has_errors = False
    for task in tasks:
        errors = validate_task(task)
        if errors:
            has_errors = True
            print(f"[FAIL] {task.get('task_id', '<unknown>')}: {errors}")
        else:
            print(f"[OK] {task['task_id']}")
    raise SystemExit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
