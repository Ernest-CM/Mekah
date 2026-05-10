from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.actions import ACTIONS, ACTION_INDEX
from ..core.features import build_context_vector
from ..core.policy_service import policy_service
from ..core.reward import compute_reward
from ..db import models
from ..schemas.api import (
    PolicyUpdateRequest,
    PolicyUpdateResponse,
    RewardComponentsModel,
    MetricsResponse,
    ActionInfo,
)
from .deps import get_db, require_decision

router = APIRouter(prefix="/api", tags=["policy"])


@router.post("/policy/update", response_model=PolicyUpdateResponse)
def update_policy(payload: PolicyUpdateRequest, db: Session = Depends(get_db)) -> PolicyUpdateResponse:
    decision = require_decision(payload.decision_id, db)

    existing = (
        db.query(models.PolicyUpdate)
        .filter(models.PolicyUpdate.decision_id == decision.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="policy already updated for this decision")

    ctx = db.get(models.ContextEvent, decision.context_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="context for decision not found")

    validation = (
        db.query(models.Validation)
        .filter(models.Validation.decision_id == decision.id)
        .first()
    )
    wcag_violations = validation.hard_failures if validation else 0

    review = (
        db.query(models.HitlReview)
        .filter(models.HitlReview.decision_id == decision.id)
        .first()
    )
    hitl_rejected = bool(review and review.decision == "reject")

    components = compute_reward(
        task_completed=payload.task_completed,
        completion_time_ms=payload.completion_time_ms,
        time_budget_ms=payload.time_budget_ms,
        error_count=payload.error_count,
        error_budget=payload.error_budget,
        trust_score=payload.trust_score,
        wcag_violations=wcag_violations,
        hitl_rejected=hitl_rejected,
    )

    x = build_context_vector(ctx.features or {})
    arm_idx = ACTION_INDEX[decision.action_id]
    new_version = policy_service.update(
        db,
        arm_idx=arm_idx,
        x=x,
        reward=components.r_final,
        notes=f"decision={decision.id} reward={components.r_final:.3f}",
    )

    update_id = str(uuid4())
    db.add(
        models.PolicyUpdate(
            id=update_id,
            decision_id=decision.id,
            action_id=decision.action_id,
            reward_components=components.__dict__,
            final_reward=components.r_final,
            wcag_violations=wcag_violations,
            hitl_rejected=hitl_rejected,
            model_version=new_version,
        )
    )
    db.commit()

    return PolicyUpdateResponse(
        update_id=update_id,
        model_version=new_version,
        final_reward=components.r_final,
        components=RewardComponentsModel(**components.__dict__),
    )


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)) -> MetricsResponse:
    total_decisions = db.query(func.count(models.Decision.id)).scalar() or 0
    total_executions = db.query(func.count(models.Execution.id)).scalar() or 0
    total_blocked = (
        db.query(func.count(models.Execution.id))
        .filter(models.Execution.was_blocked.is_(True))
        .scalar()
        or 0
    )
    total_fallbacks = (
        db.query(func.count(models.Execution.id))
        .filter(models.Execution.was_fallback.is_(True))
        .scalar()
        or 0
    )
    pending_hitl = (
        db.query(func.count(models.HitlReview.id))
        .filter(models.HitlReview.decision.is_(None))
        .scalar()
        or 0
    )
    resolved_hitl = (
        db.query(func.count(models.HitlReview.id))
        .filter(models.HitlReview.decision.is_not(None))
        .scalar()
        or 0
    )
    approved = (
        db.query(func.count(models.HitlReview.id))
        .filter(models.HitlReview.decision == "approve")
        .scalar()
        or 0
    )

    avg_reward = db.query(func.avg(models.PolicyUpdate.final_reward)).scalar()
    avg_confidence = db.query(func.avg(models.Decision.confidence)).scalar()

    arm_pulls = {a.id: arm.n_pulls for a, arm in zip(ACTIONS, policy_service.policy.arms)}
    arm_avg_reward = {
        a.id: (arm.cumulative_reward / arm.n_pulls if arm.n_pulls else 0.0)
        for a, arm in zip(ACTIONS, policy_service.policy.arms)
    }

    compliance_rate = 1.0 - (total_blocked / total_executions) if total_executions else 1.0
    approval_rate = approved / resolved_hitl if resolved_hitl else 0.0

    return MetricsResponse(
        total_decisions=int(total_decisions),
        total_executions=int(total_executions),
        total_blocked=int(total_blocked),
        total_fallbacks=int(total_fallbacks),
        compliance_rate=float(compliance_rate),
        pending_hitl=int(pending_hitl),
        resolved_hitl=int(resolved_hitl),
        approval_rate=float(approval_rate),
        avg_reward=float(avg_reward or 0.0),
        avg_confidence=float(avg_confidence or 0.0),
        model_version=policy_service.version,
        arm_pulls=arm_pulls,
        arm_avg_reward=arm_avg_reward,
    )


@router.get("/actions", response_model=list[ActionInfo])
def get_actions() -> list[ActionInfo]:
    return [
        ActionInfo(id=a.id, label=a.label, description=a.description, payload=a.payload)
        for a in ACTIONS
    ]
