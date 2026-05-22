"""Stage 5: Fill controlled requirements from requirement banks."""
from __future__ import annotations

import random
from typing import Any


def select_requirements(
    template: dict,
    variant: dict,
    entity_selection: dict,
    requirement_banks: dict[str, dict],
    diversity_state: dict | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Select requirements from controlled requirement banks.

    Returns a dict of requirement key-value pairs suitable for the template.
    """
    rng = rng or random.Random()
    ds = diversity_state or {}
    req_use_counts = ds.get("requirement_use_counts", {})
    site = template["site"]
    bank = requirement_banks.get(site, {})
    actions = template.get("allowed_actions", [])
    requirements: dict[str, Any] = {}

    for action in actions:
        if action == "comment":
            bodies = bank.get("comment_bodies", [])
            if bodies:
                selected = _pick_least_used(bodies, req_use_counts, f"{site}_comment_body", rng)
                requirements["body_must_include"] = selected

        elif action == "comment_post":
            bodies = bank.get("comment_bodies", [])
            if bodies:
                selected = _pick_least_used(bodies, req_use_counts, f"{site}_comment_body", rng)
                requirements["comment_body_must_include"] = selected
                requirements.setdefault("body_must_include", selected)

        elif action == "add_label":
            labels = bank.get("labels", [])
            if labels:
                selected = _pick_least_used_single(labels, req_use_counts, f"{site}_label", rng)
                requirements["label"] = selected

        elif action == "assign_issue":
            assignees = bank.get("assignee_usernames", [])
            if assignees:
                selected = _pick_least_used_single(
                    assignees, req_use_counts, f"{site}_assignee_username", rng
                )
                requirements["assignee_username"] = selected

        elif action in ("close_issue", "reopen_issue", "remove_from_cart"):
            pass  # No extra requirements

        elif action == "add_to_cart":
            quantities = bank.get("quantities", [1, 2, 3])
            requirements["add_to_cart_quantity"] = 1 if 1 in quantities else min(quantities)
            requirements.setdefault("quantity", requirements["add_to_cart_quantity"])

        elif action == "update_quantity":
            quantities = bank.get("quantities", [1, 2, 3])
            choices = [q for q in quantities if q != requirements.get("add_to_cart_quantity", 1)]
            requirements["update_quantity"] = rng.choice(choices or quantities)
            requirements["quantity"] = requirements["update_quantity"]

        elif action == "write_review":
            reviews = bank.get("reviews", [])
            if reviews:
                review = _pick_least_used_dict(reviews, req_use_counts, f"{site}_review", rng)
                requirements["rating"] = review.get("rating", 4)
                requirements["body_must_include"] = _as_list(review.get("body_must_include", []))

        elif action == "create_post":
            titles = bank.get("post_titles", [])
            bodies = bank.get("post_bodies", [])
            if titles:
                requirements["title_must_include"] = _pick_least_used(titles, req_use_counts, f"{site}_post_title", rng)
            if bodies:
                requirements["body_must_include"] = _pick_least_used(bodies, req_use_counts, f"{site}_post_body", rng)

        elif action == "edit_post":
            bodies = bank.get("post_bodies", [])
            if bodies:
                requirements["body_must_include"] = _pick_least_used(bodies, req_use_counts, f"{site}_post_body", rng)

        elif action == "create_page":
            titles = bank.get("page_titles", [])
            bodies = bank.get("page_bodies", [])
            if titles:
                requirements["title_must_include"] = _pick_least_used(titles, req_use_counts, f"{site}_page_title", rng)
            if bodies:
                requirements["body_must_include"] = _pick_least_used(bodies, req_use_counts, f"{site}_page_body", rng)

        elif action in ("edit_page", "publish_page"):
            if "body_must_include" not in requirements:
                page_bodies = bank.get("page_bodies", [])
                if page_bodies:
                    requirements["body_must_include"] = _pick_least_used(page_bodies, req_use_counts, f"{site}_page_body", rng)

    return requirements


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _pick_least_used(
    options: list,
    use_counts: dict,
    prefix: str,
    rng: random.Random,
) -> list[str]:
    """Pick a requirement option, preferring least-used ones. Returns list of strings."""
    if not options:
        return []
    if isinstance(options[0], list):
        scored = [(use_counts.get(f"{prefix}:{','.join(o)}", 0), o) for o in options]
    else:
        scored = [(use_counts.get(f"{prefix}:{o}", 0), [o]) for o in options]
    min_score = min(s for s, _ in scored)
    candidates = [o for s, o in scored if s <= min_score + 1]
    selected = rng.choice(candidates)
    key = f"{prefix}:{','.join(selected)}"
    use_counts[key] = use_counts.get(key, 0) + 1
    return selected


def _pick_least_used_single(
    options: list,
    use_counts: dict,
    prefix: str,
    rng: random.Random,
) -> str:
    """Pick a single string option, preferring least-used."""
    scored = [(use_counts.get(f"{prefix}:{o}", 0), o) for o in options]
    min_score = min(s for s, _ in scored)
    candidates = [o for s, o in scored if s <= min_score + 1]
    selected = rng.choice(candidates)
    use_counts[f"{prefix}:{selected}"] = use_counts.get(f"{prefix}:{selected}", 0) + 1
    return selected


def _pick_least_used_dict(
    options: list[dict],
    use_counts: dict,
    prefix: str,
    rng: random.Random,
) -> dict:
    """Pick a dict option, preferring least-used."""
    scored = [(use_counts.get(f"{prefix}:{i}", 0), i, o) for i, o in enumerate(options)]
    min_score = min(s for s, _, _ in scored)
    candidates = [(i, o) for s, i, o in scored if s <= min_score + 1]
    idx, selected = rng.choice(candidates)
    use_counts[f"{prefix}:{idx}"] = use_counts.get(f"{prefix}:{idx}", 0) + 1
    return selected
