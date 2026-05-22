"""Tests for ground truth generation."""


def test_comment_issue_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_014",
        "actions": [{"type": "comment", "body_must_include": ["needs retry logic"]}],
        "requirements": {"body_must_include": ["needs retry logic"]},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    assert gt["type"] == "expected_backend_state"
    assert len(gt["assertions"]) == 1
    a = gt["assertions"][0]
    assert a["check_object"] == "issue_comments"
    assert a["conditions"]["issue_ref"] == "gitlab_issue_014"
    assert a["conditions"]["author_ref"] == "current_user"
    assert a["must_satisfy"]["body_must_include"] == ["needs retry logic"]


def test_add_label_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_003",
        "actions": [{"type": "add_label", "label": "backend"}],
        "requirements": {"label": "backend"},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    assert len(gt["assertions"]) == 1
    a = gt["assertions"][0]
    assert a["check_object"] == "issue_labels"
    assert a["must_satisfy"]["labels_include"] == ["backend"]


def test_close_issue_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_007",
        "actions": [{"type": "close_issue"}],
        "requirements": {},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "issues"
    assert a["must_satisfy"]["state"] == "closed"


def test_assign_issue_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_003",
        "actions": [{"type": "assign_issue", "assignee_username": "dev_alice"}],
        "requirements": {"assignee_username": "dev_alice"},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "issues"
    assert a["conditions"]["issue_ref"] == "gitlab_issue_003"
    assert a["must_satisfy"]["assignee_ref"] == "dev_alice"


def test_reopen_issue_ground_truth_with_precondition():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_004",
        "actions": [{"type": "reopen_issue"}],
        "requirements": {},
        "requires_conditional": False,
    }
    template = {
        "ground_truth_rules": [],
        "preconditions": [
            {
                "resource": "issues",
                "where": {"issue_ref": "{target_entity}"},
                "assert": {"state": "closed"},
            }
        ],
    }
    gt = generate_ground_truth(task_spec, template)
    assert gt["assertions"][0]["must_satisfy"]["state"] == "open"
    assert gt["preconditions"][0]["must_satisfy"]["state"] == "closed"


def test_add_to_cart_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "shopping_variant_031",
        "actions": [{"type": "add_to_cart", "quantity": 2}],
        "requirements": {"quantity": 2},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "cart_items"
    assert a["conditions"]["variant_ref"] == "shopping_variant_031"
    assert a["must_satisfy"]["quantity"] == 2


def test_remove_from_cart_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "shopping_product_005",
        "actions": [{"type": "remove_from_cart"}],
        "requirements": {},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "cart_items"
    assert a["conditions"]["product_ref"] == "shopping_product_005"
    assert a["conditions"]["user_ref"] == "current_user"
    assert a["must_satisfy"]["exists"] is False


def test_write_review_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "shopping_product_005",
        "actions": [{"type": "write_review", "rating": 4, "body_must_include": ["comfortable"]}],
        "requirements": {"rating": 4, "body_must_include": ["comfortable"]},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "reviews"
    assert a["must_satisfy"]["rating"] == 4
    assert "comfortable" in a["must_satisfy"]["body_must_include"]


def test_comment_label_close_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_052",
        "actions": [
            {"type": "comment", "body_must_include": ["please add checkout monitoring"]},
            {"type": "add_label", "label": "monitoring"},
            {"type": "close_issue"},
        ],
        "requirements": {
            "body_must_include": ["please add checkout monitoring"],
            "label": "monitoring",
        },
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    assert len(gt["assertions"]) == 3
    check_objects = {a["check_object"] for a in gt["assertions"]}
    assert "issue_comments" in check_objects
    assert "issue_labels" in check_objects
    assert "issues" in check_objects


def test_create_post_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "forum_community_001",
        "actions": [{"type": "create_post", "title_must_include": ["car in NYC"], "body_must_include": ["public transit"]}],
        "requirements": {"title_must_include": ["car in NYC"], "body_must_include": ["public transit"]},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "posts"
    assert a["conditions"]["community_ref"] == "forum_community_001"


def test_edit_page_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "cms_page_001",
        "actions": [{"type": "edit_page", "body_must_include": ["30-day return window"]}],
        "requirements": {"body_must_include": ["30-day return window"]},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "cms_pages"
    assert a["must_satisfy"]["last_editor_ref"] == "current_user"


def test_edit_post_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "forum_post_001",
        "actions": [{"type": "edit_post", "body_must_include": ["public transit"]}],
        "requirements": {"body_must_include": ["public transit"]},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "posts"
    assert a["conditions"]["post_ref"] == "forum_post_001"
    assert a["must_satisfy"]["body_must_include"] == ["public transit"]
    assert a["must_satisfy"]["last_editor_ref"] == "current_user"


def test_create_page_ground_truth():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "cms_page_011",
        "actions": [
            {
                "type": "create_page",
                "title_must_include": ["returns help center"],
                "body_must_include": ["30-day return window"],
            }
        ],
        "requirements": {
            "title_must_include": ["returns help center"],
            "body_must_include": ["30-day return window"],
        },
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    a = gt["assertions"][0]
    assert a["check_object"] == "cms_pages"
    assert a["must_satisfy"]["exists"] is True
    assert a["must_satisfy"]["title_must_include"] == ["returns help center"]
    assert a["must_satisfy"]["creator_ref"] == "current_user"


def test_conditional_adds_preconditions():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_007",
        "actions": [{"type": "close_issue"}],
        "requirements": {},
        "requires_conditional": True,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    assert "preconditions" in gt
    assert len(gt["preconditions"]) >= 1
    assert gt["preconditions"][0]["must_satisfy"]["state"] == "open"


def test_ground_truth_binds_entity():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_099",
        "actions": [{"type": "comment", "body_must_include": ["test"]}],
        "requirements": {},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)
    entity_found = False
    for a in gt["assertions"]:
        for v in a.get("conditions", {}).values():
            if v == "gitlab_issue_099":
                entity_found = True
    assert entity_found, "Ground truth must bind to target entity"


def test_ground_truth_binds_each_action_target_entity():
    from taskgen.ground_truth import generate_ground_truth
    task_spec = {
        "target_entity": "gitlab_issue_001",
        "target_entities": {
            "A": {"entity_id": "gitlab_issue_001"},
            "B": {"entity_id": "gitlab_issue_002"},
        },
        "actions": [
            {"type": "comment", "target": "A", "body_must_include": ["alpha"]},
            {"type": "add_label", "target": "B", "label": "backend"},
        ],
        "requirements": {},
        "requires_conditional": False,
    }
    template = {"ground_truth_rules": []}
    gt = generate_ground_truth(task_spec, template)

    assert gt["assertions"][0]["conditions"]["issue_ref"] == "gitlab_issue_001"
    assert gt["assertions"][1]["conditions"]["issue_ref"] == "gitlab_issue_002"
