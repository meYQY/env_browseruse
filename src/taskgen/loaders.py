"""Stage 0: Load all pre-pipeline assets.

Reads YAML/JSON configuration from disk and returns plain dicts
compatible with the pipeline modules.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ABILITY_LABEL_MAP = {
    "memory_information_tracking": "Memory",
    "long_horizon_operation": "Long-horizon",
}
ABILITY_KEY_MAP = {v: k for k, v in ABILITY_LABEL_MAP.items()}
SITE_ALIAS = {"cms": "cms_admin"}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---- Entities ---------------------------------------------------------------

def load_entities(path: Path) -> dict[str, dict]:
    """Load normalized entities from JSON. Returns dict keyed by entity_id."""
    if not path.exists():
        logger.warning("Entity file not found: %s", path)
        return {}
    raw = _load_json(path)
    if isinstance(raw, list):
        return {e["entity_id"]: e for e in raw}
    return raw


# ---- Generation plan --------------------------------------------------------

def load_generation_plan(config_dir: Path) -> dict:
    """Load generation_plan.yaml -> pipeline-ready dict.

    Returns dict with keys: target_total, distributions, curated_examples.
    """
    path = config_dir / "generation_plan.yaml"
    if not path.exists():
        logger.warning("Generation plan not found: %s", path)
        return {"target_total": 0, "distributions": [], "curated_examples": {"specs": []}}

    raw = _load_yaml(path)
    total = raw.get("target_total_tasks", 100)
    abilities = raw.get("ability_dimensions", {})
    diff_dist = raw.get("difficulty_distribution", {})
    environments = raw.get("environments", {})

    diff_weights = {level: conf.get("target_fraction", 0.2) for level, conf in diff_dist.items()}

    distributions = []
    for ability_key, ability_conf in abilities.items():
        ability_label = ability_conf.get("label", ABILITY_LABEL_MAP.get(ability_key, ability_key))
        ability_frac = ability_conf.get("target_fraction", 0.5)

        for env_key, env_conf in environments.items():
            env_frac = env_conf.get("target_fraction", 0.25)
            site = env_conf.get("site", env_key)
            env_count = max(1, round(total * ability_frac * env_frac))
            distributions.append({
                "ability_dimension": ability_label,
                "target_environment": site,
                "count": env_count,
                "difficulty_weights": dict(diff_weights),
                "allowed_task_templates": [],
            })

    # Curated examples
    curated_raw = raw.get("curated_examples", {})
    curated_specs = []
    env_site_map = {k: v.get("site", k) for k, v in environments.items()}

    for ex in curated_raw.get("examples", []):
        ability_key = ex.get("ability", "")
        ability_label = ABILITY_LABEL_MAP.get(ability_key, ability_key)
        env_key = ex.get("environment", "")
        site = env_site_map.get(env_key, env_key)
        curated_specs.append({
            "ability_dimension": ability_label,
            "difficulty": ex.get("difficulty", "L1"),
            "target_environment": site,
        })

    return {
        "target_total": total,
        "distributions": distributions,
        "curated_examples": {"specs": curated_specs},
    }


# ---- Structure rules --------------------------------------------------------

def load_structure_rules(config_dir: Path) -> dict[str, list[dict]]:
    """Load difficulty_structure_rules.yaml.

    Returns dict keyed by "Memory_L1", "Long-horizon_L3" etc.,
    each value a list of structure variant dicts.
    """
    path = config_dir / "difficulty_structure_rules.yaml"
    if not path.exists():
        logger.warning("Structure rules not found: %s", path)
        return {}

    data = _load_yaml(path)
    result: dict[str, list[dict]] = {}

    for ability_key, levels in data.items():
        if not isinstance(levels, dict):
            continue
        if not any(isinstance(k, str) and k.startswith("L") for k in levels):
            continue

        ability_label = ABILITY_LABEL_MAP.get(ability_key, ability_key)

        for difficulty, rule in levels.items():
            if not isinstance(rule, dict):
                continue

            key = f"{ability_label}_{difficulty}"
            locators = rule.get("locator", ["direct_ref"])
            if isinstance(locators, str):
                locators = [locators]

            conditions = rule.get("conditions", {})
            actions = rule.get("actions", {})
            cond_logic = rule.get("conditional_logic", False)
            cond_mode = _parse_conditional(cond_logic)
            assertions = rule.get("assertions", 1)

            variants = []
            for loc in locators:
                family = _structure_family(ability_key, difficulty, loc, actions.get("min", 1))
                variants.append({
                    "structure_id": family,
                    "structure_family": family,
                    "locator": loc,
                    "min_locator_conditions": conditions.get("min", 0),
                    "max_locator_conditions": conditions.get("max", 1),
                    "actions_min": actions.get("min", 1),
                    "actions_max": actions.get("max", 1),
                    "requires_tracking": "memory" in ability_key,
                    "requires_conditional": cond_mode not in ("none",),
                    "conditional_mode": cond_mode,
                    "min_assertions": assertions,
                })
            result[key] = variants

    return result


def _structure_family(ability_key: str, difficulty: str, locator: str, actions_min: int) -> str:
    if ability_key == "long_horizon_operation":
        if actions_min >= 3 or difficulty == "L5":
            return f"long_horizon_{difficulty}_multi_action_chain_{locator}"
        if actions_min == 2:
            return f"long_horizon_{difficulty}_two_step_chain_{locator}"
        return f"long_horizon_{difficulty}_single_action_{locator}"
    if difficulty in ("L4", "L5"):
        return f"memory_{difficulty}_tracked_locator_{locator}"
    return f"memory_{difficulty}_lookup_{locator}"


def _parse_conditional(value: Any) -> str:
    if value is True:
        return "required"
    if value is False:
        return "none"
    if isinstance(value, str):
        return value
    return "none"


# ---- Task templates ---------------------------------------------------------

def load_task_templates(config_dir: Path) -> dict[str, dict]:
    """Load all task template YAMLs from config/task_templates/.

    Returns dict keyed by template_id with ability labels and flat difficulty lists.
    """
    templates_dir = config_dir / "task_templates"
    if not templates_dir.exists():
        logger.warning("Task templates dir not found: %s", templates_dir)
        return {}

    result: dict[str, dict] = {}
    for yaml_file in sorted(templates_dir.glob("*.yaml")):
        data = _load_yaml(yaml_file)
        if not isinstance(data, dict):
            continue
        templates = data.get("templates", data)
        if not isinstance(templates, dict):
            continue

        for tid, tmpl in templates.items():
            if not isinstance(tmpl, dict) or "site" not in tmpl:
                continue

            # Convert ability keys to labels
            compatible_abilities = []
            for ak in tmpl.get("compatible_abilities", []):
                compatible_abilities.append(ABILITY_LABEL_MAP.get(ak, ak))

            # Build per-ability difficulty map and flat list
            compat_diff = tmpl.get("compatible_difficulties", {})
            all_difficulties: set[str] = set()
            ability_difficulty_map: dict[str, list[str]] = {}
            if isinstance(compat_diff, dict):
                for ability_key, levels in compat_diff.items():
                    if isinstance(levels, list):
                        all_difficulties.update(levels)
                        label = ABILITY_LABEL_MAP.get(ability_key, ability_key)
                        ability_difficulty_map[label] = levels
            elif isinstance(compat_diff, list):
                all_difficulties.update(compat_diff)

            # Process required_entity_attributes
            req_attrs = tmpl.get("required_entity_attributes", [])
            attrs_dict = {}
            if isinstance(req_attrs, list):
                for item in req_attrs:
                    if isinstance(item, dict):
                        attrs_dict.update(item)
            elif isinstance(req_attrs, dict):
                attrs_dict = req_attrs

            # Ground truth rules with action keys
            gt_rules_raw = tmpl.get("ground_truth_rules", {})
            gt_assertions = gt_rules_raw.get("assertions", []) if isinstance(gt_rules_raw, dict) else []
            allowed_actions = tmpl.get("allowed_actions", [])

            gt_rules = []
            if len(gt_assertions) == len(allowed_actions):
                for i, action in enumerate(allowed_actions):
                    rule = dict(gt_assertions[i])
                    rule["action"] = action
                    gt_rules.append(rule)
            elif gt_assertions:
                for assertion in gt_assertions:
                    rule = dict(assertion)
                    if "action" not in rule:
                        rule["action"] = _infer_action_for_assertion(rule, allowed_actions)
                    gt_rules.append(rule)

            result[tid] = {
                "template_id": tid,
                "site": tmpl.get("site", ""),
                "required_entity_type": tmpl.get("required_entity_type", ""),
                "required_entity_attributes": attrs_dict,
                "allowed_actions": allowed_actions,
                "ground_truth_rules": gt_rules,
                "preconditions": tmpl.get("preconditions", []),
                "verifier_rules": tmpl.get("verifier_rules", {}),
                "compatible_abilities": compatible_abilities,
                "compatible_difficulties": sorted(all_difficulties),
                "ability_difficulty_map": ability_difficulty_map,
            }

    return result


def _infer_action_for_assertion(rule: dict, allowed_actions: list[str]) -> str:
    """Best-effort mapping for composite templates with combined assertions."""
    resource = rule.get("resource") or rule.get("check_object", "")
    asserted = rule.get("assert") or rule.get("must_satisfy") or {}

    if resource == "issue_comments" and "comment" in allowed_actions:
        return "comment"
    if resource == "comments" and "comment_post" in allowed_actions:
        return "comment_post"
    if resource == "issue_labels" and "add_label" in allowed_actions:
        return "add_label"
    if resource == "issues" and "assignee_ref" in asserted and "assign_issue" in allowed_actions:
        return "assign_issue"
    if resource == "issues" and asserted.get("state") == "open" and "reopen_issue" in allowed_actions:
        return "reopen_issue"
    if resource == "issues" and "close_issue" in allowed_actions:
        return "close_issue"
    if resource == "reviews" and "write_review" in allowed_actions:
        return "write_review"
    if resource == "posts" and "last_editor_ref" in asserted and "edit_post" in allowed_actions:
        return "edit_post"
    if resource == "posts" and "create_post" in allowed_actions:
        return "create_post"
    if resource == "cms_pages" and "creator_ref" in asserted and "create_page" in allowed_actions:
        return "create_page"
    if resource == "cms_pages" and "status" in asserted and "publish_page" in allowed_actions:
        return "publish_page"
    if resource == "cms_pages" and "edit_page" in allowed_actions:
        return "edit_page"
    if resource == "cart_items" and asserted.get("exists") is False and "remove_from_cart" in allowed_actions:
        return "remove_from_cart"
    if resource == "cart_items" and "update_quantity" in allowed_actions:
        return "update_quantity"
    if resource == "cart_items" and "add_to_cart" in allowed_actions:
        return "add_to_cart"
    return allowed_actions[0] if allowed_actions else "unknown"


# ---- Requirement banks ------------------------------------------------------

def load_requirement_banks(config_dir: Path) -> dict[str, dict]:
    """Load all requirement bank YAMLs. Returns dict keyed by site."""
    banks_dir = config_dir / "requirement_banks"
    if not banks_dir.exists():
        logger.warning("Requirement banks dir not found: %s", banks_dir)
        return {}

    result: dict[str, dict] = {}
    for yaml_file in sorted(banks_dir.glob("*.yaml")):
        data = _load_yaml(yaml_file)
        if data:
            site = yaml_file.stem
            site = SITE_ALIAS.get(site, site)
            result[site] = data
    return result


# ---- RuntimeContext ---------------------------------------------------------

class RuntimeContext:
    """Holds all loaded assets for the pipeline."""

    def __init__(
        self,
        config_dir: Path = Path("config"),
        data_dir: Path | None = None,
        entities_path: Path | None = None,
    ):
        self.config_dir = Path(config_dir)

        # Load entities
        if entities_path and Path(entities_path).exists():
            self.entities = load_entities(Path(entities_path))
        elif data_dir and (Path(data_dir) / "normalized" / "entities.json").exists():
            self.entities = load_entities(Path(data_dir) / "normalized" / "entities.json")
        else:
            for candidate in [
                Path("data/normalized/entities.json"),
                Path("data/entities_normalized.json"),
                Path("data/entities_sample.json"),
            ]:
                if candidate.exists():
                    self.entities = load_entities(candidate)
                    break
            else:
                self.entities = {}

        self.task_templates = load_task_templates(self.config_dir)
        self.structure_rules = load_structure_rules(self.config_dir)
        self.requirement_banks = load_requirement_banks(self.config_dir)
        self.generation_plan = load_generation_plan(self.config_dir)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.entities:
            errors.append("No entities loaded")
        if not self.task_templates:
            errors.append("No task templates loaded")
        if not self.structure_rules:
            errors.append("No structure rules loaded")
        if not self.requirement_banks:
            errors.append("No requirement banks loaded")

        sites_with_entities = {e.get("site") for e in self.entities.values()}
        for tid, tmpl in self.task_templates.items():
            if tmpl["site"] not in sites_with_entities:
                errors.append(f"Template '{tid}' site '{tmpl['site']}' has no entities")

        return errors
