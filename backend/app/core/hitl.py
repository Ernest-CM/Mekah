"""HITL trigger logic (revised.md §8.2).

Returns (requires_review, trigger_reason) for a candidate action given the
policy confidence, validator output, action payload, and user profile.
"""
from __future__ import annotations
from typing import Any
from .actions import Action
from .wcag import ValidationResult, Status
from ..config import HITL_CONFIDENCE_THRESHOLD


HIGH_IMPACT_KEYS = {"density", "hide_nonessential"}


def needs_review(
    confidence: float,
    validation: ValidationResult,
    action: Action,
    user_profile: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    if validation.status == Status.WARN:
        return True, "validator_warn"

    if confidence < HITL_CONFIDENCE_THRESHOLD:
        return True, "low_confidence"

    if any(k in (action.payload or {}) for k in HIGH_IMPACT_KEYS):
        return True, "high_impact_region"

    if user_profile and user_profile.get("vulnerable") and action.id != "A6":
        return True, "vulnerable_profile"

    return False, None
