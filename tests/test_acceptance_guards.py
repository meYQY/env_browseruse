"""Regression tests for hard output acceptance rules."""

import re


def test_generated_tasks_have_no_known_instruction_bugs(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=100)
    assert len(tasks) == 100

    forbidden = [
        "Find the gitlab entity where",
        "perform ",
        "add_label label",
        "comment with text containing",
        "write_review",
        "edit_page",
        "publish_page",
    ]
    for task in tasks:
        desc = task["task_description"]
        assert task["quality_checks"]["passed"], task
        assert not any(token in desc for token in forbidden), desc
        assert not re.search(r"([A-Za-z],\s){3,}[A-Za-z]", desc), desc


def test_generated_tasks_use_canonical_verifier_keys(runtime_ctx, fake_provider):
    from taskgen.pipeline import Pipeline
    from taskgen.quality import CANONICAL_CONDITION_KEYS

    pipeline = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=fake_provider,
        seed=42,
    )
    tasks = pipeline.run(target_count=100)
    for task in tasks:
        for assertion in task["ground_truth"].get("assertions", []):
            assert set(assertion.get("conditions", {})).issubset(CANONICAL_CONDITION_KEYS)
        for check in task["verifier"].get("checks", []):
            assert set(check["query"].get("filters", {})).issubset(CANONICAL_CONDITION_KEYS)


def test_l5_long_horizon_has_real_chain_complexity(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=100)
    l5_long = [
        t for t in tasks
        if t["ability_dimension"] == "Long-horizon" and t["difficulty"] == "L5"
    ]
    assert l5_long
    for task in l5_long:
        assert len(task["actions"]) >= 3
        assert len(task["ground_truth"]["assertions"]) >= 3


def test_curated_examples_are_quality_passed(runtime_ctx, fake_provider):
    from taskgen.pipeline import Pipeline
    from taskgen.diversity import select_curated_examples

    pipeline = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=fake_provider,
        seed=42,
    )
    tasks = pipeline.run(target_count=100)
    examples = select_curated_examples(tasks, 10)
    assert len(examples) == 10
    assert all(t["quality_checks"]["passed"] for t in examples)
    assert {t["difficulty"] for t in examples} == {"L1", "L2", "L3", "L4", "L5"}
    assert {"Memory", "Long-horizon"}.issubset({t["ability_dimension"] for t in examples})
