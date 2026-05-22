"""Tests for entity loading and normalization."""
import json
from pathlib import Path


def test_normalize_produces_entities(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    assert len(entities) >= 100, f"Expected 100+ entities, got {len(entities)}"


def test_entity_schema(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    required_keys = {"entity_id", "site", "entity_type", "attributes"}
    for e in entities:
        missing = required_keys - set(e.keys())
        assert not missing, f"Entity {e.get('entity_id')} missing keys: {missing}"


def test_entity_sites(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    sites = {e["site"] for e in entities}
    assert "gitlab" in sites
    assert "shopping" in sites
    assert "forum" in sites
    assert "cms_admin" in sites


def test_entity_types(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    types = {e["entity_type"] for e in entities}
    assert "issue" in types
    assert "product" in types
    assert "community" in types
    assert "cms_page" in types


def test_load_entities_dict(normalized_entities_path):
    from taskgen.loaders import load_entities
    entities = load_entities(normalized_entities_path)
    assert isinstance(entities, dict)
    assert len(entities) >= 100
    for eid, entity in entities.items():
        assert eid == entity["entity_id"]


def test_all_entities_have_grounding_status(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    for e in entities:
        assert e.get("grounding_status") == "symbolic_entity"


def test_attribute_richness_variety(raw_data_dir):
    from taskgen.normalizer import normalize_all
    entities = normalize_all(raw_data_dir)
    attr_counts = [len(e.get("attributes", {})) for e in entities]
    assert min(attr_counts) >= 1
    assert max(attr_counts) >= 4, "Should have entities with 4+ attributes for L4/L5"


def test_normalizer_deterministic(raw_data_dir):
    from taskgen.normalizer import normalize_all
    run1 = normalize_all(raw_data_dir)
    run2 = normalize_all(raw_data_dir)
    assert len(run1) == len(run2)
    for e1, e2 in zip(run1, run2):
        assert e1["entity_id"] == e2["entity_id"]


def test_entity_selector_skips_excluded_ids():
    import random
    from taskgen.entity_selector import select_target_entity

    entities = {
        "issue_a": {
            "entity_id": "issue_a",
            "site": "gitlab",
            "entity_type": "issue",
            "attributes": {"iid": 1, "title_contains": "alpha"},
        },
        "issue_b": {
            "entity_id": "issue_b",
            "site": "gitlab",
            "entity_type": "issue",
            "attributes": {"iid": 2, "title_contains": "beta"},
        },
    }
    template = {
        "template_id": "comment_issue",
        "site": "gitlab",
        "required_entity_type": "issue",
    }
    variant = {"min_locator_conditions": 1}

    selected = select_target_entity(
        template, variant, entities, rng=random.Random(42), exclude_ids={"issue_a"}
    )

    assert selected["entity_id"] == "issue_b"
