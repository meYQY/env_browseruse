"""Stage 7: Generate ground truth from structured task spec."""
from __future__ import annotations
from typing import Any


def generate_ground_truth(task_spec: dict, template: dict) -> dict:
    """Deterministically generate ground truth from task spec + template rules.

    Returns a ground_truth dict with assertions and optional preconditions.
    """
    actions = task_spec["actions"]
    requirements = task_spec.get("requirements", {})
    gt_rules = template.get("ground_truth_rules", [])

    assertions = []
    preconditions = []

    for action in actions:
        action_type = action["type"]
        entity_id = _entity_id_for_action(task_spec, action)
        action_requirements = _requirements_for_action(task_spec, action, requirements)
        rule = _find_rule(gt_rules, action_type)
        if action.get("final_assertion") is False and not rule:
            continue
        if rule:
            assertion = _apply_rule(rule, entity_id, action, action_requirements)
            assertions.append(assertion)
        else:
            assertion = _default_assertion(action_type, entity_id, action, action_requirements)
            assertions.append(assertion)

    for raw_precond in template.get("preconditions", []):
        target = raw_precond.get("_target")
        entity_id = _entity_id_for_target(task_spec, target)
        precond_requirements = task_spec.get("requirements_by_target", {}).get(
            target, requirements
        )
        preconditions.append(_apply_rule(raw_precond, entity_id, {}, precond_requirements))

    # Handle preconditions for conditional actions
    if task_spec.get("requires_conditional"):
        for action in actions:
            entity_id = _entity_id_for_action(task_spec, action)
            precond = _build_precondition(action, entity_id, task_spec)
            if precond:
                preconditions.append(precond)

    result = {
        "type": "expected_backend_state",
        "assertions": assertions,
    }
    if preconditions:
        result["preconditions"] = preconditions
    return result


def _entity_id_for_action(task_spec: dict, action: dict) -> str:
    return _entity_id_for_target(task_spec, action.get("target"))


def _entity_id_for_target(task_spec: dict, target: str | None) -> str:
    primary_entity = task_spec.get("target_entity", "")
    target_entities = task_spec.get("target_entities", {})
    if target and target in target_entities:
        target_entity = target_entities[target]
        if isinstance(target_entity, dict):
            return str(target_entity.get("entity_id", _coerce_entity_id(primary_entity)))
        return str(target_entity)
    return _coerce_entity_id(primary_entity)


def _coerce_entity_id(target_entity: Any) -> str:
    if isinstance(target_entity, dict):
        return str(target_entity.get("entity_id", ""))
    return str(target_entity)


def _requirements_for_action(
    task_spec: dict,
    action: dict,
    default_requirements: dict,
) -> dict:
    target = action.get("target")
    requirements_by_target = task_spec.get("requirements_by_target", {})
    if target and target in requirements_by_target:
        return requirements_by_target[target]
    return default_requirements


def _find_rule(rules: list[dict], action_type: str) -> dict | None:
    for rule in rules:
        if rule.get("action") == action_type:
            return rule
    return None


def _as_phrase_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _shopping_ref_key(entity_id: str) -> str:
    return "product_ref" if str(entity_id).startswith("shopping_product_") else "variant_ref"


def _apply_rule(rule: dict, entity_id: str, action: dict, requirements: dict) -> dict:
    """Apply a ground truth rule template with concrete values."""
    check_object = rule.get("check_object") or rule.get("resource", "unknown")
    raw_conditions = rule.get("conditions") or rule.get("where", {})
    raw_must_satisfy = rule.get("must_satisfy") or rule.get("assert", {})

    conditions = {}
    for ck, cv in raw_conditions.items():
        conditions[ck] = _resolve_placeholder(cv, entity_id, action, requirements)

    must_satisfy = {}
    for mk, mv in raw_must_satisfy.items():
        must_satisfy[mk] = _resolve_placeholder(mv, entity_id, action, requirements)

    return {
        "check_object": check_object,
        "conditions": conditions,
        "must_satisfy": must_satisfy,
    }


def _resolve_placeholder(value: Any, entity_id: str, action: dict, requirements: dict) -> Any:
    if not isinstance(value, str):
        return value
    if value == "{target_entity}":
        return entity_id
    if value == "{current_user}" or value == "current_user":
        return "current_user"
    if value.startswith("{") and value.endswith("}"):
        key = value[1:-1]
        if key in action:
            return action[key]
        if key in requirements:
            return requirements[key]
    return value


def _default_assertion(action_type: str, entity_id: str, action: dict, requirements: dict) -> dict:
    """Build a default assertion based on action type."""
    if action_type == "comment":
        return {
            "check_object": "issue_comments",
            "conditions": {"issue_ref": entity_id, "author_ref": "current_user"},
            "must_satisfy": {
                "exists": True,
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
            },
        }
    elif action_type == "add_label":
        return {
            "check_object": "issue_labels",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"labels_include": [action.get("label", requirements.get("label", ""))]},
        }
    elif action_type == "close_issue":
        return {
            "check_object": "issues",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"state": "closed"},
        }
    elif action_type == "assign_issue":
        return {
            "check_object": "issues",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"assignee_ref": action.get("assignee_username", requirements.get("assignee_username", ""))},
        }
    elif action_type == "reopen_issue":
        return {
            "check_object": "issues",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"state": "open"},
        }
    elif action_type == "add_to_cart":
        must_satisfy = {"exists": True}
        if not action.get("exists_only"):
            must_satisfy["quantity"] = action.get("quantity", requirements.get("quantity", 1))
        return {
            "check_object": "cart_items",
            "conditions": {"user_ref": "current_user", _shopping_ref_key(entity_id): entity_id},
            "must_satisfy": must_satisfy,
        }
    elif action_type == "update_quantity":
        return {
            "check_object": "cart_items",
            "conditions": {"user_ref": "current_user", _shopping_ref_key(entity_id): entity_id},
            "must_satisfy": {
                "exists": True,
                "quantity": action.get("quantity", requirements.get("quantity", 1)),
            },
        }
    elif action_type == "remove_from_cart":
        return {
            "check_object": "cart_items",
            "conditions": {"user_ref": "current_user", _shopping_ref_key(entity_id): entity_id},
            "must_satisfy": {"exists": False},
        }
    elif action_type == "write_review":
        return {
            "check_object": "reviews",
            "conditions": {"author_ref": "current_user", "product_ref": entity_id},
            "must_satisfy": {
                "exists": True,
                "rating": action.get("rating", requirements.get("rating", 4)),
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
            },
        }
    elif action_type == "create_post":
        return {
            "check_object": "posts",
            "conditions": {"community_ref": entity_id, "author_ref": "current_user"},
            "must_satisfy": {
                "exists": True,
                "title_must_include": _as_phrase_list(action.get("title_must_include", requirements.get("title_must_include", []))),
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
            },
        }
    elif action_type == "comment_post":
        return {
            "check_object": "comments",
            "conditions": {"post_ref": entity_id, "author_ref": "current_user"},
            "must_satisfy": {
                "exists": True,
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
            },
        }
    elif action_type == "edit_post":
        return {
            "check_object": "posts",
            "conditions": {"post_ref": entity_id},
            "must_satisfy": {
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
                "last_editor_ref": "current_user",
            },
        }
    elif action_type == "create_page":
        return {
            "check_object": "cms_pages",
            "conditions": {"page_ref": entity_id},
            "must_satisfy": {
                "exists": True,
                "title_must_include": _as_phrase_list(action.get("title_must_include", requirements.get("title_must_include", []))),
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
                "creator_ref": "current_user",
            },
        }
    elif action_type == "edit_page":
        return {
            "check_object": "cms_pages",
            "conditions": {"page_ref": entity_id},
            "must_satisfy": {
                "body_must_include": _as_phrase_list(action.get("body_must_include", requirements.get("body_must_include", []))),
                "last_editor_ref": "current_user",
            },
        }
    elif action_type == "publish_page":
        return {
            "check_object": "cms_pages",
            "conditions": {"page_ref": entity_id},
            "must_satisfy": {"status": "published"},
        }
    else:
        return {
            "check_object": action_type,
            "conditions": {"entity_ref": entity_id},
            "must_satisfy": {"completed": True},
        }


def _build_precondition(action: dict, entity_id: str, task_spec: dict) -> dict | None:
    action_type = action["type"]
    if action_type == "close_issue":
        return {
            "check_object": "issues",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"state": "open"},
        }
    if action_type == "reopen_issue":
        return {
            "check_object": "issues",
            "conditions": {"issue_ref": entity_id},
            "must_satisfy": {"state": "closed"},
        }
    if action_type == "add_label":
        label = action.get("label", task_spec.get("requirements", {}).get("label", ""))
        if label:
            return {
                "check_object": "issue_labels",
                "conditions": {"issue_ref": entity_id},
                "must_satisfy": {"labels_do_not_include": [label]},
            }
    if action_type == "publish_page":
        return {
            "check_object": "cms_pages",
            "conditions": {"page_ref": entity_id},
            "must_satisfy": {"status": "draft"},
        }
    return None
