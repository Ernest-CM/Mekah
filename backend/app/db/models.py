from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContextEvent(Base):
    """Captured client context at a single adaptation decision point."""
    __tablename__ = "context_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    features: Mapped[dict] = mapped_column(JSON)
    ui_state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class Decision(Base):
    """Policy decision record — one per /adapt/decide call."""
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(36), ForeignKey("context_events.id"), index=True)
    action_id: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    arm_scores: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class Validation(Base):
    """WCAG validator output for a candidate action."""
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("decisions.id"), index=True)
    status: Mapped[str] = mapped_column(String(8))
    hard_failures: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    violations: Mapped[list] = mapped_column(JSON)
    simulated_state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class HitlReview(Base):
    """Human review queue and resolution log."""
    __tablename__ = "hitl_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("decisions.id"), unique=True, index=True)
    trigger_reason: Mapped[str] = mapped_column(String(64))
    candidate_action_id: Mapped[str] = mapped_column(String(8))
    candidate_payload: Mapped[dict] = mapped_column(JSON)
    validation_summary: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)

    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewer_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Execution(Base):
    """Final applied action after gate + HITL."""
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("decisions.id"), index=True)
    applied_action_id: Mapped[str] = mapped_column(String(8))
    applied_ui_state: Mapped[dict] = mapped_column(JSON)
    was_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    was_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class PolicyUpdate(Base):
    """Reward + LinUCB update record."""
    __tablename__ = "policy_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("decisions.id"), index=True)
    action_id: Mapped[str] = mapped_column(String(8))
    reward_components: Mapped[dict] = mapped_column(JSON)
    final_reward: Mapped[float] = mapped_column(Float)
    wcag_violations: Mapped[int] = mapped_column(Integer, default=0)
    hitl_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    model_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class AxeReport(Base):
    """axe-core DOM scan result linked to a decision (post-execution, real DOM)."""
    __tablename__ = "axe_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("decisions.id"), index=True)
    violations: Mapped[list] = mapped_column(JSON)
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_serious_count: Mapped[int] = mapped_column(Integer, default=0)
    passes: Mapped[int] = mapped_column(Integer, default=0)
    incomplete: Mapped[int] = mapped_column(Integer, default=0)
    scanned_at: Mapped[str] = mapped_column(String(32))
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PolicySnapshot(Base):
    """Versioned LinUCB model parameters (A_a, b_a per arm)."""
    __tablename__ = "policy_snapshots"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    n_features: Mapped[int] = mapped_column(Integer)
    n_arms: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
