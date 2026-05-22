"""Stage 8: Generate verifier templates from ground truth."""
from __future__ import annotations
from typing import Any


def generate_verifier(ground_truth: dict) -> dict:
    """Convert ground truth assertions into DB/API checker templates.

    No live backend execution - marks as not_executed.
    """
    assertions = ground_truth.get("assertions", [])
    checks = []

    for assertion in assertions:
        check = {
            "query": {
                "resource": assertion.get("check_object", "unknown"),
                "filters": assertion.get("conditions", {}),
            },
            "condition": assertion.get("must_satisfy", {}),
        }
        checks.append(check)

    return {
        "type": "db_api_checker_template",
        "checks": checks,
        "execution_status": "not_executed",
    }


def verifier_binds_entity(verifier: dict, entity_id: str) -> bool:
    """Check that the verifier references the target entity."""
    for check in verifier.get("checks", []):
        filters = check.get("query", {}).get("filters", {})
        for v in filters.values():
            if v == entity_id:
                return True
    return False


def verifier_checks_user(verifier: dict) -> bool:
    """Check that verifier checks current_user where appropriate."""
    for check in verifier.get("checks", []):
        filters = check.get("query", {}).get("filters", {})
        for v in filters.values():
            if v == "current_user":
                return True
    return False
