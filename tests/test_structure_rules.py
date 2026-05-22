"""Tests for structure rules loading and variant selection."""
import random

import pytest


def test_load_structure_rules(config_dir):
    from taskgen.loaders import load_structure_rules
    rules = load_structure_rules(config_dir)
    assert len(rules) >= 10, f"Expected 10+ rule keys, got {len(rules)}"


def test_rule_keys_format(config_dir):
    from taskgen.loaders import load_structure_rules
    rules = load_structure_rules(config_dir)
    for key in rules:
        parts = key.split("_")
        assert parts[-1].startswith("L"), f"Key {key} should end with difficulty level"


def test_all_cells_have_variants(runtime_ctx):
    from taskgen.planning import build_generation_cells
    from taskgen.structure_rules import select_structure_variant
    rng = random.Random(42)
    cells = build_generation_cells(runtime_ctx.generation_plan)
    for cell in cells:
        variant = select_structure_variant(cell, runtime_ctx.structure_rules, rng)
        assert "structure_id" in variant
        assert "locator" in variant


def test_variant_schema(config_dir):
    from taskgen.loaders import load_structure_rules
    rules = load_structure_rules(config_dir)
    for key, variants in rules.items():
        for v in variants:
            assert "structure_id" in v
            assert "locator" in v
            assert "actions_min" in v
            assert "actions_max" in v
            assert v["actions_min"] <= v["actions_max"]


def test_memory_l1_is_simple(config_dir):
    from taskgen.loaders import load_structure_rules
    rules = load_structure_rules(config_dir)
    variants = rules.get("Memory_L1", [])
    assert len(variants) >= 1
    for v in variants:
        assert v["locator"] == "direct_ref"
        assert v["actions_max"] == 1


def test_longhorizon_l5_is_complex(config_dir):
    from taskgen.loaders import load_structure_rules
    rules = load_structure_rules(config_dir)
    variants = rules.get("Long-horizon_L5", [])
    assert len(variants) >= 1
    for v in variants:
        assert v["actions_min"] >= 2


def test_variant_no_missing_cells(runtime_ctx):
    """Every (ability, difficulty) combination must have at least one variant."""
    abilities = ["Memory", "Long-horizon"]
    difficulties = ["L1", "L2", "L3", "L4", "L5"]
    for ability in abilities:
        for diff in difficulties:
            key = f"{ability}_{diff}"
            assert key in runtime_ctx.structure_rules, f"Missing structure rule for {key}"
            assert len(runtime_ctx.structure_rules[key]) >= 1
