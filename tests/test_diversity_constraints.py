"""Tests for diversity checks and enforcement."""
from collections import Counter


def test_diversity_check(runtime_ctx, fake_provider):
    from taskgen.pipeline import Pipeline
    from taskgen.diversity import check_diversity
    pipeline = Pipeline(
        entities=runtime_ctx.entities,
        task_templates=runtime_ctx.task_templates,
        structure_rules=runtime_ctx.structure_rules,
        requirement_banks=runtime_ctx.requirement_banks,
        generation_plan=runtime_ctx.generation_plan,
        llm_provider=fake_provider,
        seed=42,
    )
    tasks = pipeline.run(target_count=50)
    stats = check_diversity(tasks)
    assert stats["total_tasks"] >= 50
    assert stats["unique_entities"] >= 10
    assert stats["unique_templates"] >= 5


def test_enforce_diversity_entity_limit():
    from taskgen.diversity import enforce_diversity
    tasks = []
    for i in range(20):
        tasks.append({
            "target_entity": {"entity_id": "e1"},
            "task_structure": {"task_template": f"t{i}"},
        })
    selected = enforce_diversity(tasks, target_count=20, max_entity_reuse=3)
    entity_counts = Counter(
        t["target_entity"]["entity_id"] for t in selected
    )
    assert entity_counts["e1"] <= 3


def test_enforce_diversity_template_ratio():
    from taskgen.diversity import enforce_diversity
    tasks = []
    for i in range(50):
        tasks.append({
            "target_entity": {"entity_id": f"e{i}"},
            "task_structure": {"task_template": "dominant_template"},
        })
    selected = enforce_diversity(tasks, target_count=50, max_template_ratio=0.4)
    template_counts = Counter(
        t["task_structure"]["task_template"] for t in selected
    )
    assert template_counts["dominant_template"] <= 20


def test_ability_distribution(runtime_ctx, fake_provider):
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
    abilities = Counter(t["ability_dimension"] for t in tasks)
    assert abilities["Memory"] >= 30, f"Too few Memory tasks: {abilities['Memory']}"
    assert abilities["Long-horizon"] >= 30, f"Too few Long-horizon tasks: {abilities['Long-horizon']}"


def test_difficulty_distribution(runtime_ctx, fake_provider):
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
    difficulties = Counter(t["difficulty"] for t in tasks)
    for level in ["L1", "L2", "L3", "L4", "L5"]:
        assert difficulties[level] >= 5, f"Too few {level} tasks: {difficulties[level]}"


def test_environment_distribution(runtime_ctx, fake_provider):
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
    envs = {t["target_environment"] for t in tasks}
    assert len(envs) >= 4


def test_curated_examples_cover_all_difficulties(runtime_ctx, fake_provider):
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
    difficulties = {t["difficulty"] for t in examples}
    assert difficulties == {"L1", "L2", "L3", "L4", "L5"}


def test_curated_examples_cover_both_abilities(runtime_ctx, fake_provider):
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
    abilities = {t["ability_dimension"] for t in examples}
    assert abilities == {"Memory", "Long-horizon"}
