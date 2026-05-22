"""Tests for task template loading and selection."""
import random


def test_load_task_templates(config_dir):
    from taskgen.loaders import load_task_templates
    templates = load_task_templates(config_dir)
    assert len(templates) >= 11, f"Expected 11+ templates, got {len(templates)}"


def test_template_schema(config_dir):
    from taskgen.loaders import load_task_templates
    templates = load_task_templates(config_dir)
    for tid, t in templates.items():
        assert t["template_id"] == tid
        assert "site" in t
        assert "allowed_actions" in t
        assert len(t["allowed_actions"]) >= 1
        assert "compatible_abilities" in t
        assert "compatible_difficulties" in t


def test_template_sites(config_dir):
    from taskgen.loaders import load_task_templates
    templates = load_task_templates(config_dir)
    sites = {t["site"] for t in templates.values()}
    assert "gitlab" in sites
    assert "shopping" in sites
    assert "forum" in sites
    assert "cms_admin" in sites


def test_template_selection(runtime_ctx):
    from taskgen.template_registry import select_task_template
    rng = random.Random(42)
    cell = {
        "ability_dimension": "Memory",
        "difficulty": "L1",
        "target_environment": "gitlab",
        "allowed_task_templates": [],
    }
    variant = {"actions_min": 1, "actions_max": 1}
    tmpl = select_task_template(cell, variant, runtime_ctx.task_templates, {}, rng)
    assert tmpl["site"] == "gitlab"
    assert "Memory" in tmpl["compatible_abilities"]


def test_template_selection_respects_environment(runtime_ctx):
    from taskgen.template_registry import select_task_template
    rng = random.Random(42)
    for env in ["gitlab", "shopping", "forum", "cms_admin"]:
        cell = {
            "ability_dimension": "Memory",
            "difficulty": "L2",
            "target_environment": env,
            "allowed_task_templates": [],
        }
        variant = {"actions_min": 1, "actions_max": 1}
        tmpl = select_task_template(cell, variant, runtime_ctx.task_templates, {}, rng)
        assert tmpl["site"] == env


def test_template_selection_least_used(runtime_ctx):
    from taskgen.template_registry import select_task_template
    rng = random.Random(42)
    cell = {
        "ability_dimension": "Memory",
        "difficulty": "L2",
        "target_environment": "gitlab",
        "allowed_task_templates": [],
    }
    variant = {"actions_min": 1, "actions_max": 1}
    ds = {"template_counts": {}}
    selected_templates = set()
    for _ in range(10):
        tmpl = select_task_template(cell, variant, runtime_ctx.task_templates, ds, rng)
        tid = tmpl["template_id"]
        ds["template_counts"][tid] = ds["template_counts"].get(tid, 0) + 1
        selected_templates.add(tid)
    assert len(selected_templates) >= 2, "Should use multiple templates for diversity"
