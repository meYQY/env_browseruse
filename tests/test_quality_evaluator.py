"""Tests for generated-vs-WebArena quality comparison."""


def test_quality_evaluator_compares_minimal_task_sets():
    from taskgen.quality_evaluator import compare_task_sets

    generated = [
        {
            "task_description": "In GitLab, find the issue with IID 18. Close the issue.",
            "target_entity": {"entity_id": "gitlab_issue_018"},
            "task_structure": {
                "locator": {"iid": 18},
                "task_template": "close_issue",
            },
            "actions": [{"type": "close_issue"}],
            "ground_truth": {
                "assertions": [
                    {
                        "check_object": "issues",
                        "conditions": {"issue_ref": "gitlab_issue_018"},
                        "must_satisfy": {"state": "closed"},
                    }
                ]
            },
            "verifier": {
                "checks": [
                    {
                        "query": {"resource": "issues", "filters": {"issue_ref": "gitlab_issue_018"}},
                        "condition": {"state": "closed"},
                    }
                ]
            },
            "validation_status": {"needs_backend_validation": True},
            "quality_checks": {"passed": True},
            "ability_dimension": "Memory",
            "difficulty": "L1",
            "target_environment": "gitlab",
        }
    ]
    webarena = [
        {
            "sites": ["shopping_admin"],
            "intent": "What is the top-1 best-selling product in 2022",
            "intent_template_id": 279,
            "instantiation_dict": {"n": 1, "year": 2022},
            "start_url": "__SHOPPING_ADMIN__",
            "eval": {
                "eval_types": ["string_match"],
                "reference_answers": {"exact_match": "Quest Lumaflex Band"},
            },
        }
    ]
    report = compare_task_sets(generated, webarena)
    assert report["generated"]["count"] == 1
    assert report["webarena_official"]["count"] == 1
    assert report["generated"]["diagnostics"]["raw_dsl_count"] == 0
    assert "comparison" in report
