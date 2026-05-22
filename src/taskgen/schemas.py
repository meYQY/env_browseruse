"""Core data schemas for the task generation framework.

All types are stdlib dataclasses -- no third-party dependencies.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    entity_id: str
    site: str
    entity_type: str
    attributes: dict[str, Any]
    relations: dict[str, str] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    grounding_status: str = "symbolic_entity"


# ---------------------------------------------------------------------------
# Generation plan
# ---------------------------------------------------------------------------

@dataclass
class GenerationCell:
    ability_dimension: str  # e.g. "memory_information_tracking", "long_horizon_operation"
    difficulty: str  # "L1" through "L5"
    target_environment: str  # "gitlab", "shopping", "forum", "cms_admin"
    target_count: int
    allowed_task_templates: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Structure / difficulty rules
# ---------------------------------------------------------------------------

@dataclass
class StructureVariant:
    structure_id: str
    locator: str  # "direct_ref", "single_condition", "multi_condition", "exclusion_condition"
    min_locator_conditions: int
    max_locator_conditions: int
    actions_min: int
    actions_max: int
    requires_tracking: bool = False
    requires_conditional: bool = False
    conditional_mode: str = "none"  # "none", "optional", "required", "true_or_initial_state_check"
    min_assertions: int = 1


# ---------------------------------------------------------------------------
# Task templates
# ---------------------------------------------------------------------------

@dataclass
class TaskTemplate:
    template_id: str
    site: str
    required_entity_type: str
    required_entity_attributes: dict[str, Any] = field(default_factory=dict)
    allowed_actions: list[str] = field(default_factory=list)
    ground_truth_rules: list[dict[str, Any]] = field(default_factory=list)
    verifier_rules: list[dict[str, Any]] = field(default_factory=list)
    compatible_abilities: list[str] = field(default_factory=list)
    compatible_difficulties: dict[str, list[str]] | list[str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Controlled requirements
# ---------------------------------------------------------------------------

@dataclass
class ControlledRequirements:
    requirements: dict[str, Any]  # e.g. {"body_must_include": ["needs retry logic"], "label": "backend"}


# ---------------------------------------------------------------------------
# Structured task spec (pre-generation intermediate)
# ---------------------------------------------------------------------------

@dataclass
class StructuredTaskSpec:
    task_id: str
    ability_dimension: str
    difficulty: str
    target_environment: str
    structure_variant: str
    task_template: str
    target_entity: str
    locator: dict[str, Any]
    actions: list[dict[str, Any]]
    requirements: dict[str, Any]


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

@dataclass
class GroundTruthAssertion:
    check_object: str
    conditions: dict[str, Any]
    must_satisfy: dict[str, Any]


@dataclass
class GroundTruth:
    type: str = "expected_backend_state"
    assertions: list[GroundTruthAssertion] = field(default_factory=list)
    preconditions: list[GroundTruthAssertion] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

@dataclass
class VerifierCheck:
    query: dict[str, Any]
    condition: dict[str, Any]


@dataclass
class VerifierTemplate:
    type: str = "db_api_checker_template"
    checks: list[VerifierCheck] = field(default_factory=list)
    execution_status: str = "not_executed"


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

@dataclass
class QualityCheckResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generated task (final output)
# ---------------------------------------------------------------------------

@dataclass
class GeneratedTask:
    task_id: str
    task_description: str
    target_environment: str
    ability_dimension: str
    difficulty: str
    target_entity: dict[str, Any]
    task_structure: dict[str, Any]
    actions: list[dict[str, Any]]
    ground_truth: dict[str, Any]
    verifier: dict[str, Any]
    validation_status: dict[str, Any]
    quality_checks: dict[str, Any]
    diversity_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (deep copy, safe for JSON)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratedTask:
        """Construct a GeneratedTask from a plain dict."""
        # Use a shallow copy so we don't mutate the caller's dict.
        d = copy.copy(data)
        return cls(
            task_id=d["task_id"],
            task_description=d["task_description"],
            target_environment=d["target_environment"],
            ability_dimension=d["ability_dimension"],
            difficulty=d["difficulty"],
            target_entity=d.get("target_entity", {}),
            task_structure=d.get("task_structure", {}),
            actions=d.get("actions", []),
            ground_truth=d.get("ground_truth", {}),
            verifier=d.get("verifier", {}),
            validation_status=d.get("validation_status", {}),
            quality_checks=d.get("quality_checks", {}),
            diversity_metadata=d.get("diversity_metadata", {}),
        )
