from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.actions import ACTIONS, ACTION_INDEX, NUM_ACTIONS, get_action
from ..core.features import build_context_vector
from ..core.policy_service import policy_service
from ..core.wcag import (
    Status,
    SAFE_FALLBACK_ACTION_ID,
    filter_allowed,
    validate_action,
)
from ..core.hitl import needs_review
from ..db import models
from ..schemas.api import (
    DecideRequest,
    DecideResponse,
    ValidateRequest,
    ExecuteRequest,
    ExecuteResponse,
)
from .deps import get_db, require_context, require_decision

router = APIRouter(prefix="/api/adapt", tags=["adapt"])


@router.post("/decide", response_model=DecideResponse)
def decide(payload: DecideRequest, db: Session = Depends(get_db)) -> DecideResponse:
    ctx = require_context(payload.context_id, db)
    user_profile = (ctx.features or {}).get("user_profile") or {}

    candidate_ids = [a.id for a in ACTIONS]
    allowed_ids = filter_allowed(ctx.ui_state or {}, user_profile, candidate_ids)
    allowed_idx = [ACTION_INDEX[aid] for aid in allowed_ids]

    x = build_context_vector(ctx.features or {})
    arm_idx, confidence, scores = policy_service.select(x, allowed_idx)

    chosen = ACTIONS[arm_idx]
    validation = validate_action(ctx.ui_state or {}, chosen.id, user_profile)
    requires_hitl, trigger = needs_review(confidence, validation, chosen, user_profile)

    decision_id = str(uuid4())
    db.add(
        models.Decision(
            id=decision_id,
            context_id=ctx.id,
            action_id=chosen.id,
            confidence=confidence,
            arm_scores={a.id: float(scores[ACTION_INDEX[a.id]]) for a in ACTIONS},
            model_version=policy_service.version,
        )
    )
    val_dict = validation.to_dict()
    db.add(
        models.Validation(
            id=str(uuid4()),
            decision_id=decision_id,
            status=val_dict["status"],
            hard_failures=val_dict["hard_failures"],
            warnings=val_dict["warnings"],
            violations=val_dict["violations"],
            simulated_state=val_dict["simulated_state"],
        )
    )

    if requires_hitl:
        db.add(
            models.HitlReview(
                id=str(uuid4()),
                decision_id=decision_id,
                trigger_reason=trigger or "unknown",
                candidate_action_id=chosen.id,
                candidate_payload=chosen.payload,
                validation_summary=val_dict,
                confidence=confidence,
            )
        )
    db.commit()

    return DecideResponse(
        decision_id=decision_id,
        context_id=ctx.id,
        action_id=chosen.id,
        action_label=chosen.label,
        action_payload=chosen.payload,
        confidence=confidence,
        arm_scores={a.id: float(scores[ACTION_INDEX[a.id]]) for a in ACTIONS},
        model_version=policy_service.version,
        requires_hitl=requires_hitl,
        hitl_trigger=trigger,
        validation=val_dict,
    )


@router.post("/validate")
def validate(payload: ValidateRequest, db: Session = Depends(get_db)) -> dict:
    ctx = require_context(payload.context_id, db)
    if payload.action_id not in ACTION_INDEX:
        raise HTTPException(status_code=400, detail=f"unknown action_id {payload.action_id}")
    user_profile = (ctx.features or {}).get("user_profile") or {}
    result = validate_action(ctx.ui_state or {}, payload.action_id, user_profile)
    return result.to_dict()


@router.post("/execute", response_model=ExecuteResponse)
def execute(payload: ExecuteRequest, db: Session = Depends(get_db)) -> ExecuteResponse:
    decision = require_decision(payload.decision_id, db)
    ctx = require_context(decision.context_id, db)
    user_profile = (ctx.features or {}).get("user_profile") or {}

    review = (
        db.query(models.HitlReview)
        .filter(models.HitlReview.decision_id == decision.id)
        .first()
    )

    proposed_action_id = decision.action_id
    block_reason: str | None = None
    was_blocked = False
    was_fallback = False

    if review is not None and review.decision in ("reject", None):
        if review.decision == "reject":
            proposed_action_id = SAFE_FALLBACK_ACTION_ID
            was_fallback = True
            block_reason = "hitl_rejected"
        else:
            proposed_action_id = SAFE_FALLBACK_ACTION_ID
            was_fallback = True
            block_reason = "hitl_pending_or_timeout"

    final_validation = validate_action(ctx.ui_state or {}, proposed_action_id, user_profile)
    if final_validation.status == Status.FAIL:
        was_blocked = True
        was_fallback = True
        block_reason = block_reason or "wcag_hard_fail"
        proposed_action_id = SAFE_FALLBACK_ACTION_ID
        final_validation = validate_action(ctx.ui_state or {}, proposed_action_id, user_profile)

    chosen = get_action(proposed_action_id)
    applied_state = final_validation.simulated_state

    execution_id = str(uuid4())
    db.add(
        models.Execution(
            id=execution_id,
            decision_id=decision.id,
            applied_action_id=proposed_action_id,
            applied_ui_state=applied_state,
            was_blocked=was_blocked,
            was_fallback=was_fallback,
            block_reason=block_reason,
        )
    )
    db.commit()

    return ExecuteResponse(
        execution_id=execution_id,
        decision_id=decision.id,
        applied_action_id=proposed_action_id,
        applied_ui_state=applied_state,
        was_blocked=was_blocked,
        was_fallback=was_fallback,
        block_reason=block_reason,
    )


# ─── axe-core report ─────────────────────────────────────────────────────────

class _AxeViolationIn(BaseModel):
    id: str
    impact: str
    description: str
    help: str
    sc_references: list[str] = []
    node_count: int = 0


class _AxeReportIn(BaseModel):
    decision_id: str
    violations: list[_AxeViolationIn]
    passes: int = 0
    incomplete: int = 0
    scanned_at: str


@router.post("/axe-report")
def axe_report(payload: _AxeReportIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Receive an axe-core DOM scan result from the frontend and persist it.

    This closes the two-stage validation loop (revised.md §4.5):
      Stage 1: Python WCAG Safety Shield — pre-action, simulated state
      Stage 2: axe-core — post-execution, real rendered DOM (this endpoint)
    """
    decision = db.get(models.Decision, payload.decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    critical_serious = sum(
        1 for v in payload.violations if v.impact in ("critical", "serious")
    )

    db.add(
        models.AxeReport(
            id=str(uuid4()),
            decision_id=payload.decision_id,
            violations=[v.model_dump() for v in payload.violations],
            violation_count=len(payload.violations),
            critical_serious_count=critical_serious,
            passes=payload.passes,
            incomplete=payload.incomplete,
            scanned_at=payload.scanned_at,
        )
    )
    db.commit()
    return {"ok": True}
