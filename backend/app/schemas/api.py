from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class ContextRequest(BaseModel):
    user_id: str
    session_id: str
    context_features: dict[str, Any] = Field(default_factory=dict)
    ui_state: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class ContextResponse(BaseModel):
    context_id: str


class DecideRequest(BaseModel):
    context_id: str


class DecideResponse(BaseModel):
    decision_id: str
    context_id: str
    action_id: str
    action_label: str
    action_payload: dict[str, Any]
    confidence: float
    arm_scores: dict[str, float]
    model_version: int
    requires_hitl: bool
    hitl_trigger: str | None
    validation: dict[str, Any]


class ValidateRequest(BaseModel):
    context_id: str
    action_id: str


class HitlReviewSubmitRequest(BaseModel):
    decision_id: str
    decision: Literal["approve", "reject", "override"]
    reviewer_id: str
    reviewer_role: Literal["accessibility_reviewer", "product_owner", "system"]
    reason: str | None = None


class HitlReviewItem(BaseModel):
    review_id: str
    decision_id: str
    context_id: str
    candidate_action_id: str
    candidate_action_label: str
    candidate_payload: dict[str, Any]
    trigger_reason: str
    confidence: float
    validation_summary: dict[str, Any]
    user_id: str
    session_id: str
    created_at: str


class ExecuteRequest(BaseModel):
    decision_id: str
    user_outcome: dict[str, Any] | None = None


class ExecuteResponse(BaseModel):
    execution_id: str
    decision_id: str
    applied_action_id: str
    applied_ui_state: dict[str, Any]
    was_blocked: bool
    was_fallback: bool
    block_reason: str | None


class RewardComponentsModel(BaseModel):
    r_task: float
    r_time: float
    r_error: float
    r_trust: float
    p_wcag: float
    r_base: float
    r_final: float
    hitl_penalty: float = 0.0


class PolicyUpdateRequest(BaseModel):
    decision_id: str
    task_completed: bool
    completion_time_ms: float
    time_budget_ms: float
    error_count: int
    error_budget: int
    trust_score: float = Field(ge=0.0, le=1.0)


class PolicyUpdateResponse(BaseModel):
    update_id: str
    model_version: int
    final_reward: float
    components: RewardComponentsModel


class MetricsResponse(BaseModel):
    total_decisions: int
    total_executions: int
    total_blocked: int
    total_fallbacks: int
    compliance_rate: float
    pending_hitl: int
    resolved_hitl: int
    approval_rate: float
    avg_reward: float
    avg_confidence: float
    model_version: int
    arm_pulls: dict[str, int]
    arm_avg_reward: dict[str, float]


class ActionInfo(BaseModel):
    id: str
    label: str
    description: str
    payload: dict[str, Any]
