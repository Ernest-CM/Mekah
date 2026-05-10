from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from ..core.actions import get_action, ACTION_INDEX
from ..db import models
from ..schemas.api import HitlReviewItem, HitlReviewSubmitRequest
from .deps import get_db

router = APIRouter(prefix="/api/hitl", tags=["hitl"])


@router.get("/queue", response_model=list[HitlReviewItem])
def get_queue(db: Session = Depends(get_db)) -> list[HitlReviewItem]:
    rows = db.execute(
        select(models.HitlReview)
        .where(models.HitlReview.decision.is_(None))
        .order_by(desc(models.HitlReview.created_at))
        .limit(100)
    ).scalars().all()

    out: list[HitlReviewItem] = []
    for r in rows:
        decision = db.get(models.Decision, r.decision_id)
        ctx = db.get(models.ContextEvent, decision.context_id) if decision else None
        if decision is None or ctx is None:
            continue
        action = get_action(r.candidate_action_id)
        out.append(
            HitlReviewItem(
                review_id=r.id,
                decision_id=r.decision_id,
                context_id=ctx.id,
                candidate_action_id=r.candidate_action_id,
                candidate_action_label=action.label,
                candidate_payload=r.candidate_payload,
                trigger_reason=r.trigger_reason,
                confidence=r.confidence,
                validation_summary=r.validation_summary,
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                created_at=r.created_at.isoformat(),
            )
        )
    return out


@router.post("/review")
def submit_review(payload: HitlReviewSubmitRequest, db: Session = Depends(get_db)) -> dict:
    review = (
        db.query(models.HitlReview)
        .filter(models.HitlReview.decision_id == payload.decision_id)
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="review not found for decision_id")
    if review.decision is not None:
        raise HTTPException(status_code=409, detail=f"already resolved as {review.decision}")

    if payload.decision == "override" and payload.reviewer_role != "product_owner":
        raise HTTPException(
            status_code=403,
            detail="override requires reviewer_role=product_owner (revised.md §8.1)",
        )
    if payload.decision == "override" and not payload.reason:
        raise HTTPException(
            status_code=400,
            detail="override requires a written reason (revised.md §8.3)",
        )

    review.decision = payload.decision
    review.reviewer_id = payload.reviewer_id
    review.reviewer_role = payload.reviewer_role
    review.reason = payload.reason
    review.is_override = payload.decision == "override"
    review.resolved_at = datetime.now(timezone.utc)

    db.commit()
    return {"ok": True, "decision": review.decision, "is_override": review.is_override}
