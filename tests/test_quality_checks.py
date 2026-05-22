"""Tests for quality check system."""


def test_quality_checks_pass_for_valid_task(runtime_ctx, fake_provider):
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
        qc = task["quality_checks"]
        assert qc["passed"], f"Task {task['task_id']} failed quality: {qc}"


def test_reject_missing_entity():
    from taskgen.quality import run_quality_checks
    task_spec = {
        "target_entity": "nonexistent_entity",
        "task_template": "comment_issue",
        "actions": [{"type": "comment"}],
        "requirements": {},
        "locator": {},
        "ability_dimension": "Memory",
        "difficulty": "L1",
        "target_environment": "gitlab",
    }
    gt = {"assertions": [{"check_object": "issue_comments", "conditions": {"issue": "nonexistent_entity"}, "must_satisfy": {}}]}
    verifier = {"checks": [{"query": {"resource": "issue_comments", "filters": {"issue": "nonexistent_entity"}}, "condition": {}}]}
    result = run_quality_checks(task_spec, "test description", gt, verifier, {}, {}, {})
    assert not result["checks"]["entity_exists"]
    assert not result["passed"]


def test_reject_incompatible_entity_type():
    from taskgen.quality import run_quality_checks
    entities = {"e1": {"entity_id": "e1", "entity_type": "product", "site": "shopping", "attributes": {}}}
    templates = {"comment_issue": {"required_entity_type": "issue", "site": "gitlab"}}
    task_spec = {
        "target_entity": "e1",
        "task_template": "comment_issue",
        "actions": [{"type": "comment"}],
        "requirements": {},
        "locator": {},
        "ability_dimension": "Memory",
        "difficulty": "L1",
        "target_environment": "gitlab",
    }
    gt = {"assertions": [{"check_object": "x", "conditions": {"issue": "e1"}, "must_satisfy": {}}]}
    verifier = {"checks": [{"query": {"resource": "x", "filters": {"issue": "e1"}}, "condition": {}}]}
    result = run_quality_checks(task_spec, "test", gt, verifier, entities, templates, {})
    assert not result["checks"]["entity_type_matches"]


def test_reject_no_ground_truth():
    from taskgen.quality import run_quality_checks
    entities = {"e1": {"entity_id": "e1", "entity_type": "issue", "site": "gitlab", "attributes": {}}}
    templates = {"comment_issue": {"required_entity_type": "issue"}}
    task_spec = {
        "target_entity": "e1",
        "task_template": "comment_issue",
        "actions": [{"type": "comment"}],
        "requirements": {},
        "locator": {},
        "ability_dimension": "Memory",
        "difficulty": "L1",
        "target_environment": "gitlab",
    }
    gt = {"assertions": []}
    verifier = {"checks": []}
    result = run_quality_checks(task_spec, "test", gt, verifier, entities, templates, {})
    assert not result["checks"]["has_ground_truth"]


def test_reject_subjective_description():
    from taskgen.quality import run_quality_checks
    entities = {"e1": {"entity_id": "e1", "entity_type": "issue", "site": "gitlab", "attributes": {}}}
    templates = {"comment_issue": {"required_entity_type": "issue"}}
    task_spec = {
        "target_entity": "e1",
        "task_template": "comment_issue",
        "actions": [{"type": "comment"}],
        "requirements": {},
        "locator": {},
        "ability_dimension": "Memory",
        "difficulty": "L1",
        "target_environment": "gitlab",
    }
    gt = {"assertions": [{"check_object": "x", "conditions": {"issue": "e1"}, "must_satisfy": {}}]}
    verifier = {"checks": [{"query": {"resource": "x", "filters": {"issue": "e1"}}, "condition": {}}]}
    result = run_quality_checks(
        task_spec,
        "Write a high quality and creative comment in your own words",
        gt, verifier, entities, templates, {},
    )
    assert not result["checks"]["no_subjective"]


def test_quality_checks_have_all_check_names(runtime_ctx, fake_provider):
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
    tasks = pipeline.run(target_count=5)
    expected_checks = {
        "entity_exists", "entity_type_matches", "locator_supported",
        "has_ground_truth", "gt_binds_entity", "verifier_binds_entity",
        "requirements_from_bank", "no_subjective", "has_labels",
        "honest_validation",
    }
    for task in tasks:
        check_keys = set(task["quality_checks"]["checks"].keys())
        missing = expected_checks - check_keys
        assert not missing, f"Missing checks: {missing}"
