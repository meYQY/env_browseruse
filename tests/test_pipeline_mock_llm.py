"""Integration tests for the full pipeline with mock LLM."""
import random


def test_pipeline_generates_10_tasks(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=10)
    assert len(tasks) >= 10


def test_pipeline_generates_100_tasks(runtime_ctx, fake_provider):
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
    assert len(tasks) >= 100


def test_pipeline_task_schema(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=10)
    required_keys = {
        "task_id", "task_description", "target_environment",
        "ability_dimension", "difficulty", "target_entity",
        "task_structure", "actions", "ground_truth", "verifier",
        "validation_status", "quality_checks", "diversity_metadata",
    }
    for task in tasks:
        missing = required_keys - set(task.keys())
        assert not missing, f"Task {task['task_id']} missing: {missing}"


def test_pipeline_multi_entity_shape_for_long_horizon_l5(runtime_ctx, fake_provider):
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
    l5_task = next(
        task for task in tasks
        if task["ability_dimension"] == "Long-horizon" and task["difficulty"] == "L5"
    )

    assert set(l5_task["target_entities"]) == {"A", "B", "C"}
    assert l5_task["target_entity"] == l5_task["target_entities"]["A"]
    assert l5_task["task_structure"]["target_entities"] == l5_task["target_entities"]
    assert {action.get("target") for action in l5_task["actions"]} == {"A", "B", "C"}

    entity_ids = {
        target: summary["entity_id"]
        for target, summary in l5_task["target_entities"].items()
    }
    assertion_entities = {
        value
        for assertion in l5_task["ground_truth"]["assertions"]
        for value in assertion.get("conditions", {}).values()
        if value in entity_ids.values()
    }
    assert set(entity_ids.values()).issubset(assertion_entities)


def test_pipeline_validation_status_honest(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=10)
    for task in tasks:
        vs = task["validation_status"]
        assert vs["symbolic_grounded"] is True
        assert vs["backend_grounded"] is False
        assert vs["verifier_executed"] is False
        assert vs["needs_backend_validation"] is True


def test_pipeline_all_verifiers_not_executed(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=10)
    for task in tasks:
        assert task["verifier"]["execution_status"] == "not_executed"


def test_pipeline_ground_truth_has_assertions(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=10)
    for task in tasks:
        gt = task["ground_truth"]
        assert len(gt.get("assertions", [])) >= 1


def test_pipeline_reproducible(runtime_ctx, fake_provider):
    from taskgen.pipeline import Pipeline
    from taskgen.llm.fake import FakeProvider
    p1 = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=FakeProvider(),
        seed=42,
    )
    p2 = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=FakeProvider(),
        seed=42,
    )
    tasks1 = p1.run(target_count=20)
    tasks2 = p2.run(target_count=20)
    assert len(tasks1) == len(tasks2)
    for t1, t2 in zip(tasks1, tasks2):
        assert t1["task_id"] == t2["task_id"]
        assert t1["task_description"] == t2["task_description"]


def test_curated_examples(runtime_ctx, fake_provider):
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
    from taskgen.diversity import select_curated_examples
    examples = select_curated_examples(tasks, 10)
    assert len(examples) == 10
    abilities = {t["ability_dimension"] for t in examples}
    difficulties = {t["difficulty"] for t in examples}
    assert "Memory" in abilities
    assert "Long-horizon" in abilities
    assert len(difficulties) == 5


def test_fake_provider_no_network():
    from taskgen.llm.fake import FakeProvider
    fp = FakeProvider()
    result = fp.generate_instruction({"target_entity": "test", "actions": [{"type": "comment"}]})
    assert isinstance(result, str)
    assert len(result) > 0
    assert fp.call_count == 1
