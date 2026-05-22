"""Stage 4: Select target entity compatible with template and structure."""
from __future__ import annotations

import random
from typing import Any


def count_usable_locator_fields(entity: dict) -> int:
    """Count how many attributes can serve as locator conditions."""
    attrs = entity.get("attributes", {})
    count = 0
    for k, v in attrs.items():
        if v is None or v == "" or v == []:
            continue
        count += 1
    return count


def entity_matches_template(entity: dict, template: dict) -> bool:
    """Check if entity type matches template requirements."""
    if entity["entity_type"] != template["required_entity_type"]:
        return False
    required_attrs = template.get("required_entity_attributes", {})
    for attr_key, attr_val in required_attrs.items():
        entity_val = entity.get("attributes", {}).get(attr_key)
        if attr_val is not None and entity_val != attr_val:
            return False
    return True


def select_target_entity(
    template: dict,
    variant: dict,
    entities: dict[str, dict],
    diversity_state: dict | None = None,
    rng: random.Random | None = None,
    exclude_ids: set | None = None,
) -> dict:
    """Select an entity compatible with template and structure variant."""
    rng = rng or random.Random()
    ds = diversity_state or {}
    entity_use_counts = ds.get("entity_use_counts", {})
    min_conditions = variant.get("min_locator_conditions", 0)
    excluded = exclude_ids or set()

    candidates = []
    for eid, entity in entities.items():
        if eid in excluded:
            continue
        if entity["site"] != template["site"]:
            continue
        if not entity_matches_template(entity, template):
            continue
        usable = count_usable_locator_fields(entity)
        if usable < min_conditions:
            continue
        candidates.append((eid, entity, usable))

    if not candidates:
        raise ValueError(
            f"No compatible entity for template {template.get('template_id', '?')} "
            f"with {min_conditions}+ locator conditions"
        )

    # Prefer less-used entities
    min_use = min(entity_use_counts.get(eid, 0) for eid, _, _ in candidates)
    least_used = [(eid, e, u) for eid, e, u in candidates if entity_use_counts.get(eid, 0) <= min_use + 1]
    if least_used:
        candidates = least_used

    locator_type = variant.get("locator", "")
    if locator_type == "ranking_or_recent":
        ranked = [
            c for c in candidates
            if any(k in c[1].get("attributes", {}) for k in ("sort_order", "post_count", "has_reviews", "price_range"))
        ]
        if ranked:
            candidates = ranked

    eid, entity, usable = rng.choice(candidates)

    # Select locator fields
    attrs = entity.get("attributes", {})
    available_fields = {k: v for k, v in attrs.items() if v is not None and v != "" and v != []}
    field_keys = _ordered_locator_fields(locator_type, list(available_fields.keys()))
    rng.shuffle(field_keys)
    field_keys = _ordered_locator_fields(locator_type, field_keys)

    num_conditions = min(
        max(min_conditions, 1),
        len(field_keys),
        variant.get("max_locator_conditions", len(field_keys)),
    )
    if min_conditions > 0:
        num_conditions = max(num_conditions, min_conditions)
    num_conditions = min(num_conditions, len(field_keys))

    selected_fields = {k: available_fields[k] for k in field_keys[:num_conditions]}
    selected_fields = _expand_until_unique(
        selected_fields, field_keys, available_fields, entity, entities, variant
    )

    if locator_type == "exclusion_condition":
        selected_fields["_locator_hint"] = "exclude alternatives that do not match all listed conditions"
    elif locator_type == "ranking_or_recent":
        selected_fields["_locator_hint"] = "use the ranking or recency-like field to disambiguate"

    return {
        "entity_id": eid,
        "site": entity["site"],
        "entity_type": entity["entity_type"],
        "full_attributes": attrs,
        "selected_locator_fields": selected_fields,
    }


def _ordered_locator_fields(locator_type: str, keys: list[str]) -> list[str]:
    if locator_type == "direct_ref":
        priority = ["iid", "sku", "post_id", "url_key", "product_name", "community_name", "page_title_contains", "title_contains"]
    elif locator_type == "ranking_or_recent":
        priority = ["sort_order", "post_count", "has_reviews", "price_range", "iid", "product_name", "title_contains"]
    else:
        priority = ["iid", "sku", "post_id", "state", "status", "labels", "category", "product_name", "title_contains", "page_title_contains"]
    rank = {k: i for i, k in enumerate(priority)}
    return sorted(keys, key=lambda k: rank.get(k, len(priority) + keys.index(k)))


def _matches(entity: dict, selected_fields: dict) -> bool:
    attrs = entity.get("attributes", {})
    for key, value in selected_fields.items():
        if key.startswith("_"):
            continue
        if attrs.get(key) != value:
            return False
    return True


def _expand_until_unique(
    selected_fields: dict,
    field_keys: list[str],
    available_fields: dict,
    entity: dict,
    entities: dict[str, dict],
    variant: dict,
) -> dict:
    max_conditions = variant.get("max_locator_conditions", len(field_keys))
    target_site = entity.get("site")
    target_type = entity.get("entity_type")

    def match_count(fields: dict) -> int:
        return sum(
            1
            for candidate in entities.values()
            if candidate.get("site") == target_site
            and candidate.get("entity_type") == target_type
            and _matches(candidate, fields)
        )

    for key in field_keys:
        if match_count(selected_fields) <= 1:
            break
        if len([k for k in selected_fields if not k.startswith("_")]) >= max_conditions:
            break
        if key not in selected_fields:
            selected_fields[key] = available_fields[key]
    return selected_fields
