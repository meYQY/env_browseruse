"""Tests for verifier template generation."""


def test_verifier_from_comment_gt():
    from taskgen.ground_truth import generate_ground_truth
    from taskgen.verifier import generate_verifier
    task_spec = {
        "target_entity": "gitlab_issue_014",
        "actions": [{"type": "comment", "body_must_include": ["needs retry logic"]}],
        "requirements": {"body_must_include": ["needs retry logic"]},
        "requires_conditional": False,
    }
    gt = generate_ground_truth(task_spec, {"ground_truth_rules": []})
    verifier = generate_verifier(gt)
    assert verifier["type"] == "db_api_checker_template"
    assert verifier["execution_status"] == "not_executed"
    assert len(verifier["checks"]) == 1
    check = verifier["checks"][0]
    assert check["query"]["resource"] == "issue_comments"
    assert check["query"]["filters"]["issue_ref"] == "gitlab_issue_014"


def test_verifier_mirrors_ground_truth_count():
    from taskgen.ground_truth import generate_ground_truth
    from taskgen.verifier import generate_verifier
    task_spec = {
        "target_entity": "gitlab_issue_052",
        "actions": [
            {"type": "comment", "body_must_include": ["test"]},
            {"type": "add_label", "label": "bug"},
            {"type": "close_issue"},
        ],
        "requirements": {"body_must_include": ["test"], "label": "bug"},
        "requires_conditional": False,
    }
    gt = generate_ground_truth(task_spec, {"ground_truth_rules": []})
    verifier = generate_verifier(gt)
    assert len(verifier["checks"]) == len(gt["assertions"])


def test_verifier_binds_entity():
    from taskgen.verifier import generate_verifier, verifier_binds_entity
    gt = {
        "assertions": [
            {
                "check_object": "issues",
                "conditions": {"issue": "gitlab_issue_007"},
                "must_satisfy": {"state": "closed"},
            }
        ]
    }
    verifier = generate_verifier(gt)
    assert verifier_binds_entity(verifier, "gitlab_issue_007")
    assert not verifier_binds_entity(verifier, "gitlab_issue_999")


def test_verifier_checks_user():
    from taskgen.verifier import generate_verifier, verifier_checks_user
    gt = {
        "assertions": [
            {
                "check_object": "issue_comments",
                "conditions": {"issue": "gitlab_issue_014", "author": "current_user"},
                "must_satisfy": {"exists": True},
            }
        ]
    }
    verifier = generate_verifier(gt)
    assert verifier_checks_user(verifier)


def test_verifier_no_user_for_close():
    from taskgen.verifier import generate_verifier, verifier_checks_user
    gt = {
        "assertions": [
            {
                "check_object": "issues",
                "conditions": {"issue": "gitlab_issue_007"},
                "must_satisfy": {"state": "closed"},
            }
        ]
    }
    verifier = generate_verifier(gt)
    assert not verifier_checks_user(verifier)


def test_verifier_not_executed():
    from taskgen.verifier import generate_verifier
    gt = {
        "assertions": [
            {
                "check_object": "cart_items",
                "conditions": {"user": "current_user", "variant": "shopping_variant_001"},
                "must_satisfy": {"exists": True, "quantity": 3},
            }
        ]
    }
    verifier = generate_verifier(gt)
    assert verifier["execution_status"] == "not_executed"
