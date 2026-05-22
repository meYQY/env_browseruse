from .base import LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic mock provider for tests -- no network calls."""

    def __init__(self):
        self.call_count = 0

    def generate_instruction(self, structured_task: dict) -> str:
        self.call_count += 1

        actions = structured_task.get("actions", [])
        target_entities = structured_task.get("target_entities", {})
        locator = structured_task.get("locator", {})
        env = structured_task.get("target_environment", "unknown")
        entity_type = structured_task.get("entity_type", "item")

        lead = f"In {_site_name(env)}, "
        if target_entities:
            lead += _target_entities_phrase(target_entities)
        else:
            lead += f"find {_entity_name(entity_type)}"
        if locator and not target_entities:
            lead += " " + _locator_phrase(locator)
        lead += "."

        multi = len(target_entities) > 1
        steps = []
        for action in actions:
            action_type = action.get("type", "unknown")
            phrase = _action_phrase(action_type, action, target_entities if multi else None)
            if phrase:
                steps.append(phrase)

        return " ".join([lead] + steps).strip()

    def judge_ambiguity(self, task_description: str, structured_task: dict) -> dict:
        self.call_count += 1
        return {"clear": True, "issues": []}


def _site_name(site: str) -> str:
    return {
        "gitlab": "GitLab",
        "shopping": "the shopping site",
        "forum": "the forum",
        "cms_admin": "the CMS admin",
    }.get(site, site)


def _entity_name(entity_type: str) -> str:
    return {
        "issue": "the issue",
        "product": "the product",
        "product_variant": "the product variant",
        "community": "the community",
        "post": "the post",
        "cms_page": "the page",
    }.get(entity_type, "the item")


def _labelize(key: str) -> str:
    return key.replace("_contains", "").replace("_", " ")


def _value_phrase(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _locator_phrase(locator: dict) -> str:
    parts = []
    for key, value in locator.items():
        if key.startswith("_"):
            continue
        label = _labelize(key)
        if key in ("iid", "sku"):
            parts.append(f"with {label.upper()} {_value_phrase(value)}")
        elif isinstance(value, bool):
            parts.append(f"with {label} set to {str(value).lower()}")
        else:
            parts.append(f"whose {label} is {_value_phrase(value)}")
    return " and ".join(parts)


def _target_entities_phrase(target_entities: dict) -> str:
    parts = []
    for target, summary in target_entities.items():
        entity_type = summary.get("entity_type", "item")
        locator = summary.get("selected_locator_fields", {})
        phrase = f"find {_entity_name(entity_type)}"
        if locator:
            phrase += " " + _locator_phrase(locator)
        parts.append(phrase)
    return "; then ".join(parts)


def _phrases(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value)


def _action_phrase(action_type: str, action: dict, target_entities: dict = None) -> str:
    prefix = _target_prefix(action, target_entities)
    if action_type == "comment":
        return f"{prefix}Add a comment containing \"{_phrases(action.get('body_must_include'))}\"."
    if action_type == "add_label":
        return f"{prefix}Add the \"{action.get('label', '')}\" label."
    if action_type == "assign_issue":
        return f"{prefix}Assign the issue to {action.get('assignee_username', '')}."
    if action_type == "close_issue":
        return f"{prefix}Close the issue."
    if action_type == "reopen_issue":
        return f"{prefix}Reopen the issue."
    if action_type == "add_to_cart":
        return f"{prefix}Add it to the cart with quantity {action.get('quantity', 1)}."
    if action_type == "update_quantity":
        return f"{prefix}Update the cart quantity to {action.get('quantity', 1)}."
    if action_type == "remove_from_cart":
        return f"{prefix}Remove it from the cart."
    if action_type == "write_review":
        return (
            f"{prefix}Write a {action.get('rating', 4)}-star review containing "
            f"\"{_phrases(action.get('body_must_include'))}\"."
        )
    if action_type == "create_post":
        return (
            f"{prefix}Create a post with a title containing \"{_phrases(action.get('title_must_include'))}\" "
            f"and a body containing \"{_phrases(action.get('body_must_include'))}\"."
        )
    if action_type == "comment_post":
        return f"{prefix}Add a comment containing \"{_phrases(action.get('body_must_include'))}\"."
    if action_type == "edit_post":
        return f"{prefix}Edit the post body so it contains \"{_phrases(action.get('body_must_include'))}\"."
    if action_type == "create_page":
        return (
            f"{prefix}Create a page with a title containing \"{_phrases(action.get('title_must_include'))}\" "
            f"and a body containing \"{_phrases(action.get('body_must_include'))}\"."
        )
    if action_type == "edit_page":
        return f"{prefix}Edit the page body so it contains \"{_phrases(action.get('body_must_include'))}\"."
    if action_type == "publish_page":
        return f"{prefix}Publish the page."
    return ""


def _short_entity_ref(summary: dict) -> str:
    entity_type = summary.get("entity_type", "item")
    locator = summary.get("selected_locator_fields", {})
    name = _entity_name(entity_type)
    for key in ("iid", "title_contains", "page_title_contains", "product_name", "community_name"):
        if key in locator:
            value = locator[key]
            if key == "iid":
                return f"{name} #{value}"
            if key in ("title_contains", "page_title_contains"):
                return f"{name} titled {_value_phrase(value)}"
            if key == "product_name":
                return f"{name} named {_value_phrase(value)}"
            if key == "community_name":
                return f"{name} called {_value_phrase(value)}"
    for key, value in locator.items():
        if key.startswith("_"):
            continue
        return f"{name} with {_labelize(key)} {_value_phrase(value)}"
    return name


def _target_prefix(action: dict, target_entities: dict = None) -> str:
    target = action.get("target")
    if not target:
        return ""
    if not target_entities or len(target_entities) <= 1:
        return ""
    summary = target_entities.get(target, {})
    ref = _short_entity_ref(summary)
    return f"For {ref}: "
