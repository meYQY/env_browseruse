"""Minimal task generator for symbolic browser-use task construction.

This is a prototype. The entity database stores only symbolic entities and their
attributes/relations. Task families are external rules. Generated tasks are
outputs, not part of the entity database.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fill_template(obj: Any, values: Dict[str, Any]) -> Any:
    """Recursively fill simple {placeholder} strings in a JSON-like template."""
    if isinstance(obj, dict):
        return {k: fill_template(v, values) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fill_template(v, values) for v in obj]
    if isinstance(obj, str):
        if obj.startswith("{") and obj.endswith("}"):
            key = obj[1:-1]
            return values.get(key, obj)
        return obj.format(**{k: v for k, v in values.items() if isinstance(v, (str, int, float))})
    return obj


def make_assertion(task_family: Dict[str, Any], target_entity: str, params: Dict[str, Any]) -> Dict[str, Any]:
    values = {"target_entity": target_entity, **params}
    return fill_template(task_family["ground_truth_template"], values)


def build_verifier(assertions: List[Dict[str, Any]]) -> Dict[str, Any]:
    checks = []
    for assertion in assertions:
        checks.append(
            {
                "query": {
                    "resource": assertion["resource"],
                    "filters": assertion.get("where", {}),
                },
                "condition": assertion.get("assert", {}),
            }
        )
    return {"verifier_type": "db_api_state_checker", "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, default=Path("data/entities_sample.json"))
    parser.add_argument("--families", type=Path, default=Path("configs/task_families.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/generated_from_rules.json"))
    args = parser.parse_args()

    entities = {e["entity_id"]: e for e in load_json(args.entities)}
    families = load_json(args.families)

    # A tiny hand-authored recipe list for demo purposes. In the full system,
    # this list is produced by sampling entities and compatible task families.
    recipes = [
        {
            "task_id": "demo_gitlab_comment_001",
            "target_entity": "gitlab_issue_014",
            "task_family": "comment_issue",
            "params": {"body_must_include": ["needs retry logic"]},
            "description": "Open the database timeout issue and comment needs retry logic.",
            "difficulty": "L1",
            "ability_dimension": "memory_information_tracking",
        },
        {
            "task_id": "demo_shopping_cart_001",
            "target_entity": "shopping_variant_031",
            "task_family": "add_to_cart",
            "params": {"quantity": 2},
            "description": "Add the black medium Quest Lumaflex Band variant to the cart with quantity 2.",
            "difficulty": "L2",
            "ability_dimension": "memory_information_tracking",
        },
    ]

    generated = []
    for recipe in recipes:
        entity = entities[recipe["target_entity"]]
        family = families[recipe["task_family"]]
        if entity["site"] != family["site"] or entity["entity_type"] != family["required_entity_type"]:
            raise ValueError(f"Entity {entity['entity_id']} is incompatible with task family {recipe['task_family']}")
        assertion = make_assertion(family, entity["entity_id"], recipe["params"])
        task = {
            "task_id": recipe["task_id"],
            "task_description": recipe["description"],
            "target_environment": entity["site"],
            "ability_dimension": recipe["ability_dimension"],
            "difficulty": recipe["difficulty"],
            "target_entity_ref": entity["entity_id"],
            "task_family": recipe["task_family"],
            "ground_truth": {
                "ground_truth_type": "expected_backend_state",
                "assertions": [assertion],
                "grounding_status": "symbolic_grounded",
            },
            "verifier": build_verifier([assertion]),
        }
        generated.append(task)

    save_json(generated, args.output)
    print(f"Wrote {len(generated)} generated tasks to {args.output}")


if __name__ == "__main__":
    main()
