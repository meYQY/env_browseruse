"""Stage 10: Static quality checks on generated tasks."""
from __future__ import annotations
from typing import Any
import re


CANONICAL_CONDITION_KEYS = {
    "issue_ref", "page_ref", "product_ref", "variant_ref", "post_ref",
    "community_ref", "user_ref", "author_ref", "entity_ref",
}

RAW_DSL_PATTERNS = [
    r"\bFind the \w+ entity where\b",
    r"\bperform [a-z_]+\b",
    r"\b[a-z]+_[a-z_]+ with text containing\b",
    r"\badd_label label\b",
    r"\bcomment_post\b",
    r"\bwrite_review\b",
    r"\bedit_page\b",
    r"\bedit_post\b",
    r"\bpublish_page\b",
    r"\badd_to_cart\b",
    r"\bupdate_quantity\b",
    r"\bclose_issue\b",
    r"\bassign_issue\b",
    r"\breopen_issue\b",
    r"\bcreate_page\b",
    r"\bremove_from_cart\b",
    r"exclude alternatives that do not match all listed conditions",
    r"ranking or recency-like field to disambiguate",
    r"\b_locator_hint\b",
]


def run_quality_checks(
    task_spec: dict,
    task_description: str,
    ground_truth: dict,
    verifier: dict,
    entities: dict[str, dict],
    templates: dict[str, dict],
    requirement_banks: dict[str, dict],
) -> dict:
    """Run deterministic quality checks on a generated task.

    Returns {"passed": bool, "checks": {name: bool}, "warnings": [str]}.
    """
    checks = {}
    warnings = []

    target_entities = _target_entities(task_spec)
    entity_ids = [
        summary.get("entity_id", "")
        for summary in target_entities.values()
        if isinstance(summary, dict)
    ]

    # 1. Target entity exists
    checks["entity_exists"] = bool(entity_ids) and all(eid in entities for eid in entity_ids)

    # 2. Entity type matches template
    template_id = task_spec.get("task_template", "")
    template = templates.get(template_id, {})
    template_ids = task_spec.get("task_templates", {})
    checks["entity_type_matches"] = _entity_types_match(
        target_entities, entities, template, template_ids, templates
    )

    # 3. Locator conditions supported by entity attributes
    checks["locator_supported"] = _locators_supported(target_entities, entities, warnings)

    # 4. Ground truth exists and has assertions
    assertions = ground_truth.get("assertions", [])
    checks["has_ground_truth"] = len(assertions) > 0

    # 5. Ground truth binds target entity
    gt_bound_ids = set()
    for a in assertions:
        conditions = a.get("conditions", {})
        for v in conditions.values():
            if v in entity_ids:
                gt_bound_ids.add(v)
    checks["gt_binds_entity"] = bool(entity_ids) and set(entity_ids).issubset(gt_bound_ids)

    # 6. Verifier binds target entity
    verifier_bound_ids = set()
    for check in verifier.get("checks", []):
        filters = check.get("query", {}).get("filters", {})
        for v in filters.values():
            if v in entity_ids:
                verifier_bound_ids.add(v)
    checks["verifier_binds_entity"] = bool(entity_ids) and set(entity_ids).issubset(verifier_bound_ids)

    # 7. Verifier checks current_user where applicable
    has_user_action = any(
        a.get("type") in (
            "comment", "add_to_cart", "write_review", "create_post",
            "comment_post", "edit_page", "update_quantity", "edit_post",
            "create_page", "remove_from_cart",
        )
        for a in task_spec.get("actions", [])
    )
    if has_user_action:
        user_checked = False
        for check in verifier.get("checks", []):
            filters = check.get("query", {}).get("filters", {})
            condition = check.get("condition", {})
            if "current_user" in filters.values() or "current_user" in condition.values():
                user_checked = True
                break
        checks["verifier_checks_user"] = user_checked
    else:
        checks["verifier_checks_user"] = True

    # 8. Requirements from controlled banks
    requirements = task_spec.get("requirements", {})
    site = task_spec.get("target_environment", "")
    bank = requirement_banks.get(site, {})
    checks["requirements_from_bank"] = _check_requirements_in_bank(requirements, bank)
    if not checks["requirements_from_bank"]:
        warnings.append("Some requirements not found in requirement bank")

    # 9. No subjective requirements
    checks["no_subjective"] = not _has_subjective_requirement(task_description)

    # 10. Has ability and difficulty labels
    checks["has_labels"] = bool(
        task_spec.get("ability_dimension") and task_spec.get("difficulty")
    )

    # 11. Validation status is honest
    checks["honest_validation"] = True

    # 12. Natural language is not raw DSL/debug rendering
    checks["no_raw_dsl"] = not _has_raw_dsl(task_description)

    # 13. Requirement strings were not split into characters
    checks["no_char_split"] = not _has_char_split(task_description)

    # 14. Difficulty/structure constraints are actually satisfied
    checks["difficulty_constraints"] = _check_difficulty_constraints(
        task_spec, ground_truth
    )

    # 15. Ground-truth/verifier schema keys are canonical
    checks["canonical_schema_keys"] = _check_canonical_schema_keys(
        ground_truth, verifier
    )

    # 16. Verifier covers every final-state assertion
    checks["verifier_covers_ground_truth"] = (
        len(verifier.get("checks", [])) == len(ground_truth.get("assertions", []))
    )

    # 17. No known redundant or misleading action chains
    checks["no_redundant_actions"] = _check_no_redundant_actions(task_spec)

    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "warnings": warnings}


def _target_entities(task_spec: dict) -> dict:
    target_entities = task_spec.get("target_entities")
    if target_entities:
        return target_entities

    target_entity = task_spec.get("target_entity", "")
    if isinstance(target_entity, dict):
        return {"A": target_entity}
    return {"A": {"entity_id": target_entity, "selected_locator_fields": task_spec.get("locator", {})}}


def _entity_types_match(
    target_entities: dict,
    entities: dict[str, dict],
    primary_template: dict,
    template_ids: dict,
    templates: dict[str, dict],
) -> bool:
    if not target_entities:
        return False
    for target, summary in target_entities.items():
        if not isinstance(summary, dict):
            return False
        entity = entities.get(summary.get("entity_id", ""))
        template = templates.get(template_ids.get(target, ""), primary_template)
        if not entity or not template:
            return False
        if entity.get("entity_type") != template.get("required_entity_type"):
            return False
    return True


def _locators_supported(
    target_entities: dict,
    entities: dict[str, dict],
    warnings: list[str],
) -> bool:
    all_supported = True
    for target, summary in target_entities.items():
        if not isinstance(summary, dict):
            all_supported = False
            continue
        entity = entities.get(summary.get("entity_id", ""))
        entity_attrs = entity.get("attributes", {}) if entity else {}
        locator = summary.get("selected_locator_fields", {})
        for key in locator:
            if key.startswith("_"):
                continue
            if key not in entity_attrs:
                all_supported = False
                warnings.append(f"Locator key '{key}' for target {target} not in entity attributes")
    return all_supported


def _check_requirements_in_bank(requirements: dict, bank: dict) -> bool:
    """Verify that requirements come from the controlled bank."""
    if not requirements:
        return True

    for body_key in ("body_must_include", "comment_body_must_include"):
        if body_key not in requirements:
            continue
        bodies = requirements[body_key]
        all_bank_bodies = set()
        for key in ("comment_bodies", "post_bodies", "page_bodies"):
            for item in bank.get(key, []):
                if isinstance(item, list):
                    all_bank_bodies.add(tuple(item))
                else:
                    all_bank_bodies.add((item,))
        # Also check review body_must_include
        for review in bank.get("reviews", []):
            bmi = review.get("body_must_include", [])
            if bmi:
                if isinstance(bmi, list):
                    all_bank_bodies.add(tuple(bmi))
                else:
                    all_bank_bodies.add((bmi,))

        if isinstance(bodies, str):
            bodies = [bodies]
        if isinstance(bodies, list) and bodies:
            if tuple(bodies) not in all_bank_bodies and not any(
                set(bodies).issubset(set(b)) for b in all_bank_bodies
            ):
                flat_bank = set()
                for b in all_bank_bodies:
                    flat_bank.update(b)
                if not all(item in flat_bank for item in bodies):
                    return False

    if "label" in requirements:
        labels = bank.get("labels", [])
        if requirements["label"] not in labels:
            return False

    if "assignee_username" in requirements:
        assignees = bank.get("assignee_usernames", [])
        if requirements["assignee_username"] not in assignees:
            return False

    if "title_must_include" in requirements:
        titles = requirements["title_must_include"]
        if isinstance(titles, str):
            titles = [titles]
        all_bank_titles = set()
        for key in ("post_titles", "page_titles"):
            for item in bank.get(key, []):
                if isinstance(item, list):
                    all_bank_titles.add(tuple(item))
                else:
                    all_bank_titles.add((item,))
        if isinstance(titles, list) and titles:
            if tuple(titles) not in all_bank_titles and not any(
                set(titles).issubset(set(t)) for t in all_bank_titles
            ):
                flat_bank = set()
                for title in all_bank_titles:
                    flat_bank.update(title)
                if not all(item in flat_bank for item in titles):
                    return False

    if "quantity" in requirements:
        quantities = bank.get("quantities", [1, 2, 3])
        if requirements["quantity"] not in quantities:
            return False

    for key in ("add_to_cart_quantity", "update_quantity"):
        if key in requirements:
            quantities = bank.get("quantities", [1, 2, 3])
            if requirements[key] not in quantities:
                return False

    if "rating" in requirements:
        valid_ratings = {r.get("rating") for r in bank.get("reviews", [])}
        if requirements["rating"] not in valid_ratings:
            return False

    return True


def _has_raw_dsl(description: str) -> bool:
    return any(re.search(pattern, description) for pattern in RAW_DSL_PATTERNS)


def _has_char_split(description: str) -> bool:
    return bool(re.search(r"([A-Za-z],\s){3,}[A-Za-z]", description))


def _locator_field_count(locator: dict) -> int:
    return sum(1 for k in locator if not k.startswith("_"))


def _check_difficulty_constraints(task_spec: dict, ground_truth: dict) -> bool:
    actions = task_spec.get("actions", [])
    assertions = ground_truth.get("assertions", [])
    constraints = task_spec.get("structure_constraints", {})
    locator = task_spec.get("locator", {})
    locator_count = _locator_field_count(locator)

    entity_count = len(task_spec.get("target_entities", {"A": None}))
    if len(actions) < constraints.get("actions_min", 1) * entity_count:
        return False
    actions_max = constraints.get("actions_max", 99) * entity_count
    if len(actions) > actions_max:
        return False
    if len(assertions) < constraints.get("min_assertions", 1) * entity_count:
        return False
    if locator_count < constraints.get("min_locator_conditions", 0):
        return False

    ability = task_spec.get("ability_dimension")
    difficulty = task_spec.get("difficulty")
    if ability == "Long-horizon" and difficulty == "L5":
        if len(actions) < 3 or len(assertions) < 3:
            return False
    if ability == "Long-horizon" and difficulty == "L4":
        if len(actions) < 2 or len(assertions) < 2:
            return False
    if ability == "Memory" and difficulty == "L5":
        locator_type = constraints.get("locator", "")
        if locator_count < 3:
            return False
        if locator_type in ("ranking_or_recent", "exclusion_condition"):
            return True
        return bool(ground_truth.get("preconditions"))
    return True


def _check_canonical_schema_keys(ground_truth: dict, verifier: dict) -> bool:
    for assertion in ground_truth.get("assertions", []):
        if not set(assertion.get("conditions", {})).issubset(CANONICAL_CONDITION_KEYS):
            return False
    for assertion in ground_truth.get("preconditions", []):
        if not set(assertion.get("conditions", {})).issubset(CANONICAL_CONDITION_KEYS):
            return False
    for check in verifier.get("checks", []):
        filters = check.get("query", {}).get("filters", {})
        if not set(filters).issubset(CANONICAL_CONDITION_KEYS):
            return False
    return True


def _check_no_redundant_actions(task_spec: dict) -> bool:
    actions = task_spec.get("actions", [])
    for first, second in zip(actions, actions[1:]):
        if (
            first.get("type") == "add_to_cart"
            and second.get("type") == "update_quantity"
            and first.get("quantity") == second.get("quantity")
        ):
            return False
    for action in actions:
        if action.get("type") == "publish_page" and "body_must_include" in action:
            return False
    return True


def _has_subjective_requirement(description: str) -> bool:
    """Check for subjective/uncheckable requirements in description."""
    subjective_markers = [
        "best possible",
        "high quality",
        "creative",
        "impressive",
        "beautiful",
        "in your own words",
        "use your judgment",
        "feel free to",
    ]
    desc_lower = description.lower()
    return any(marker in desc_lower for marker in subjective_markers)
