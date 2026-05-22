"""Main generation pipeline: stages 0-12."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from . import planning
from . import structure_rules as sr
from . import template_registry as tr
from . import entity_selector as es
from . import requirement_selector as rs
from . import ground_truth as gt_mod
from . import verifier as vf
from . import instruction_generator as ig
from . import quality as qa
from . import diversity as dv
from . import exporter


class Pipeline:
    def __init__(
        self,
        entities: dict[str, dict],
        task_templates: dict[str, dict],
        structure_rules: dict[str, list[dict]],
        requirement_banks: dict[str, dict],
        generation_plan: dict,
        llm_provider: Any,
        seed: int = 42,
        strict: bool = False,
    ):
        self.entities = entities
        self.task_templates = task_templates
        self.structure_rules = structure_rules
        self.requirement_banks = requirement_banks
        self.generation_plan = generation_plan
        self.llm_provider = llm_provider
        self.rng = random.Random(seed)
        self.strict = strict

        self.diversity_state: dict = {
            "template_counts": {},
            "entity_use_counts": {},
            "requirement_use_counts": {},
        }
        self.generated: list[dict] = []
        self.rejected: list[dict] = []
        self.task_counter = 0

    def run(self, target_count: int = 100) -> list[dict]:
        """Run the full generation pipeline."""
        cells = planning.build_generation_cells(self.generation_plan)
        candidates = []

        for cell in cells:
            cell_target = cell.get("target_count", 1)
            cell_generated = 0
            max_attempts = cell_target * 5

            for attempt in range(max_attempts):
                if cell_generated >= cell_target:
                    break
                try:
                    task = self._generate_one(cell)
                    if task:
                        candidates.append(task)
                        cell_generated += 1
                except (ValueError, KeyError):
                    continue

        # Diversity enforcement
        selected = dv.enforce_diversity(candidates, target_count)
        self.generated = selected
        return selected

    def run_curated(self, count: int = 10) -> list[dict]:
        """Generate curated example set."""
        cells = planning.build_curated_cells(self.generation_plan)
        candidates = []

        for cell in cells:
            try:
                task = self._generate_one(cell)
                if task:
                    candidates.append(task)
            except (ValueError, KeyError):
                continue

        # If not enough from curated cells, generate more from general plan
        if len(candidates) < count:
            extra_cells = planning.build_generation_cells(self.generation_plan)
            self.rng.shuffle(extra_cells)
            for cell in extra_cells:
                if len(candidates) >= count * 2:
                    break
                try:
                    task = self._generate_one(cell)
                    if task:
                        candidates.append(task)
                except (ValueError, KeyError):
                    continue

        return dv.select_curated_examples(candidates, count)

    def _generate_one(self, cell: dict) -> dict | None:
        """Generate a single task from a generation cell. Returns None on failure."""
        self.task_counter += 1
        task_id = f"task_{self.task_counter:04d}"

        # Stage 2: Select structure variant
        variant = sr.select_structure_variant(cell, self.structure_rules, self.rng)

        entity_count = self._get_entity_count(
            cell["ability_dimension"], cell["difficulty"]
        )
        slot_names = ["A", "B", "C"][:entity_count]
        target_entities = {}
        target_entity_selections = {}
        templates_by_target = {}
        requirements_by_target = {}
        actions = []
        used_entity_ids = set()

        # Stages 3-6: Build one independently-selected entity/action slot at a time.
        for target in slot_names:
            template = tr.select_task_template(
                cell, variant, self.task_templates, self.diversity_state, self.rng
            )
            template_id = template["template_id"]
            self.diversity_state["template_counts"][template_id] = (
                self.diversity_state["template_counts"].get(template_id, 0) + 1
            )

            entity_selection = es.select_target_entity(
                template, variant, self.entities, self.diversity_state, self.rng,
                exclude_ids=used_entity_ids,
            )
            entity_id = entity_selection["entity_id"]
            used_entity_ids.add(entity_id)
            self.diversity_state["entity_use_counts"][entity_id] = (
                self.diversity_state["entity_use_counts"].get(entity_id, 0) + 1
            )

            requirements = rs.select_requirements(
                template, variant, entity_selection,
                self.requirement_banks, self.diversity_state, self.rng
            )
            target_actions = self._build_actions(template, requirements, target)

            templates_by_target[target] = template
            requirements_by_target[target] = requirements
            target_entity_selections[target] = entity_selection
            target_entities[target] = self._entity_summary(entity_selection)
            actions.extend(target_actions)

        primary_target = "A"
        primary_template = templates_by_target[primary_target]
        primary_template_id = primary_template["template_id"]
        primary_entity_selection = target_entity_selections[primary_target]
        primary_entity_id = primary_entity_selection["entity_id"]
        primary_requirements = requirements_by_target[primary_target]
        template_ids_by_target = {
            target: template["template_id"]
            for target, template in templates_by_target.items()
        }
        combined_template = {
            "ground_truth_rules": [
                rule
                for template in templates_by_target.values()
                for rule in template.get("ground_truth_rules", [])
            ],
            "preconditions": [
                {**precondition, "_target": target}
                for target, template in templates_by_target.items()
                for precondition in template.get("preconditions", [])
            ],
        }

        task_spec = {
            "task_id": task_id,
            "ability_dimension": cell["ability_dimension"],
            "difficulty": cell["difficulty"],
            "target_environment": cell["target_environment"],
            "structure_variant": variant.get("structure_id", "default"),
            "task_template": primary_template_id,
            "task_templates": template_ids_by_target,
            "target_entity": primary_entity_id,
            "target_entities": target_entities,
            "locator": primary_entity_selection.get("selected_locator_fields", {}),
            "actions": actions,
            "requirements": primary_requirements,
            "requirements_by_target": requirements_by_target,
            "requires_conditional": variant.get("requires_conditional", False),
            "structure_constraints": {
                "actions_min": variant.get("actions_min", 1),
                "actions_max": variant.get("actions_max", 99),
                "min_assertions": variant.get("min_assertions", 1),
                "min_locator_conditions": variant.get("min_locator_conditions", 0),
                "locator": variant.get("locator", ""),
            },
        }

        # Stage 7: Generate ground truth
        ground_truth = gt_mod.generate_ground_truth(task_spec, combined_template)

        # Stage 8: Generate verifier template
        verifier = vf.generate_verifier(ground_truth)

        # Stage 9: Generate natural-language instruction
        task_description = ig.generate_instruction(
            task_spec, primary_entity_selection, ground_truth, self.llm_provider
        )

        # Stage 10: Quality checks
        quality_result = qa.run_quality_checks(
            task_spec, task_description, ground_truth, verifier,
            self.entities, self.task_templates, self.requirement_banks,
        )

        if not quality_result["passed"]:
            self.rejected.append({
                "task_id": task_id,
                "rejection_reason": "quality_check_failed",
                "quality_checks": quality_result,
            })
            return None

        # Build final task object
        validation_status = {
            "symbolic_grounded": True,
            "backend_grounded": False,
            "verifier_executed": False,
            "needs_backend_validation": True,
        }

        return {
            "task_id": task_id,
            "task_description": task_description,
            "target_environment": cell["target_environment"],
            "ability_dimension": cell["ability_dimension"],
            "difficulty": cell["difficulty"],
            "target_entity": target_entities[primary_target],
            "target_entities": target_entities,
            "task_structure": {
                "task_template": primary_template_id,
                "task_templates": template_ids_by_target,
                "structure_variant": variant.get("structure_id", "default"),
                "locator": primary_entity_selection.get("selected_locator_fields", {}),
                "target_entities": target_entities,
                "actions": actions,
                "requirements": primary_requirements,
                "requirements_by_target": requirements_by_target,
            },
            "actions": actions,
            "ground_truth": ground_truth,
            "verifier": verifier,
            "validation_status": validation_status,
            "quality_checks": quality_result,
            "diversity_metadata": {
                "entity_use_count": self.diversity_state["entity_use_counts"].get(primary_entity_id, 1),
                "template_use_count": self.diversity_state["template_counts"].get(primary_template_id, 1),
            },
        }

    def _get_entity_count(self, ability_dimension: str, difficulty: str) -> int:
        """Return how many independent target entities this task should use."""
        if ability_dimension == "Memory":
            return 1
        if ability_dimension == "Long-horizon":
            if difficulty in ("L3", "L4"):
                return 2
            if difficulty == "L5":
                return 3
        return 1

    def _entity_summary(self, entity_selection: dict) -> dict:
        return {
            "entity_id": entity_selection["entity_id"],
            "site": entity_selection["site"],
            "entity_type": entity_selection["entity_type"],
            "selected_locator_fields": entity_selection.get("selected_locator_fields", {}),
        }

    def _build_actions(self, template: dict, requirements: dict, target: str = "A") -> list[dict]:
        """Build action list from template and requirements."""
        actions = []
        for action_name in template.get("allowed_actions", []):
            action = {"type": action_name, "target": target}

            if action_name in ("comment", "comment_post"):
                if action_name == "comment_post" and "comment_body_must_include" in requirements:
                    action["body_must_include"] = requirements["comment_body_must_include"]
                elif "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "add_label":
                if "label" in requirements:
                    action["label"] = requirements["label"]

            elif action_name == "assign_issue":
                if "assignee_username" in requirements:
                    action["assignee_username"] = requirements["assignee_username"]

            elif action_name in ("close_issue", "reopen_issue"):
                pass

            elif action_name == "add_to_cart":
                if "update_quantity" in template.get("allowed_actions", []):
                    action["quantity"] = requirements.get("add_to_cart_quantity", 1)
                    action["exists_only"] = True
                elif "quantity" in requirements:
                    action["quantity"] = requirements["quantity"]
                if "remove_from_cart" in template.get("allowed_actions", []):
                    action["final_assertion"] = False

            elif action_name == "update_quantity":
                action["quantity"] = requirements.get(
                    "update_quantity", requirements.get("quantity", 2)
                )

            elif action_name == "remove_from_cart":
                pass

            elif action_name == "write_review":
                if "rating" in requirements:
                    action["rating"] = requirements["rating"]
                if "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "create_post":
                if "title_must_include" in requirements:
                    action["title_must_include"] = requirements["title_must_include"]
                if "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "edit_page":
                if "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "edit_post":
                if "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "create_page":
                if "title_must_include" in requirements:
                    action["title_must_include"] = requirements["title_must_include"]
                if "body_must_include" in requirements:
                    action["body_must_include"] = requirements["body_must_include"]

            elif action_name == "publish_page":
                pass

            actions.append(action)
        return actions

    def export_all(self, output_dir: Path) -> None:
        """Export all outputs."""
        if self.generated:
            exporter.export_tasks_json(self.generated, output_dir / "generated_tasks_100.json")
            exporter.export_tasks_csv(self.generated, output_dir / "generated_tasks_100.csv")

            examples = dv.select_curated_examples(self.generated, 10)
            exporter.export_tasks_json(examples, output_dir / "generated_10_examples.json")
            exporter.export_examples_markdown(examples, output_dir / "generated_10_examples.md")

            diversity_stats = dv.check_diversity(self.generated)
            exporter.export_generation_report(
                self.generated, self.rejected, diversity_stats,
                output_dir / "generation_report.json"
            )
