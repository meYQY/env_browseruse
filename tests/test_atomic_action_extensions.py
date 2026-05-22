"""Tests for extended atomic action plumbing."""
import random


def test_new_templates_load(config_dir):
    from taskgen.loaders import load_task_templates

    templates = load_task_templates(config_dir)
    for template_id in {
        "assign_issue",
        "comment_assign_close",
        "reopen_and_assign",
        "reopen_comment_label",
        "create_and_edit_post",
        "create_comment_edit",
        "create_and_publish_page",
        "add_review_remove",
    }:
        assert template_id in templates


def test_requirement_selector_new_controlled_values(runtime_ctx):
    from taskgen.requirement_selector import select_requirements

    rng = random.Random(7)
    assign_reqs = select_requirements(
        runtime_ctx.task_templates["assign_issue"],
        {},
        {},
        runtime_ctx.requirement_banks,
        {"requirement_use_counts": {}},
        rng,
    )
    assert assign_reqs["assignee_username"] in runtime_ctx.requirement_banks["gitlab"]["assignee_usernames"]

    cms_reqs = select_requirements(
        runtime_ctx.task_templates["create_and_publish_page"],
        {},
        {},
        runtime_ctx.requirement_banks,
        {"requirement_use_counts": {}},
        rng,
    )
    assert cms_reqs["title_must_include"][0] in runtime_ctx.requirement_banks["cms_admin"]["page_titles"]
    assert cms_reqs["body_must_include"][0] in runtime_ctx.requirement_banks["cms_admin"]["page_bodies"]


def test_build_actions_for_new_atomic_params(runtime_ctx, fake_provider):
    from taskgen.pipeline import Pipeline

    pipeline = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=fake_provider,
        seed=42,
    )

    actions = pipeline._build_actions(
        runtime_ctx.task_templates["comment_assign_close"],
        {
            "body_must_include": ["needs retry logic"],
            "assignee_username": "dev_alice",
        },
    )
    assert actions == [
        {"type": "comment", "target": "A", "body_must_include": ["needs retry logic"]},
        {"type": "assign_issue", "target": "A", "assignee_username": "dev_alice"},
        {"type": "close_issue", "target": "A"},
    ]

    cart_actions = pipeline._build_actions(
        runtime_ctx.task_templates["add_review_remove"],
        {"rating": 4, "body_must_include": ["comfortable"], "quantity": 1},
    )
    assert cart_actions[0]["type"] == "add_to_cart"
    assert cart_actions[0]["final_assertion"] is False
    assert cart_actions[-1] == {"type": "remove_from_cart", "target": "A"}
