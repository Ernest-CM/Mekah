"""Reward calculator (revised.md §4.4).

r_task   = +1 if task_step completed within threshold else 0
r_time   = -min(1, completion_time / time_budget)
r_error  = -error_count_normalized
r_trust  = normalized_user_feedback in [0,1]

r_base   = 0.4*r_task + 0.2*r_time + 0.2*r_error + 0.2*r_trust
p_wcag   = lambda * v_t
r_t      = r_base - p_wcag
"""
from __future__ import annotations
from dataclasses import dataclass
from ..config import REWARD_WEIGHTS, WCAG_PENALTY_LAMBDA, HITL_REJECT_PENALTY


@dataclass
class RewardComponents:
    r_task: float
    r_time: float
    r_error: float
    r_trust: float
    p_wcag: float
    r_base: float
    r_final: float
    hitl_penalty: float = 0.0


def compute_reward(
    task_completed: bool,
    completion_time_ms: float,
    time_budget_ms: float,
    error_count: int,
    error_budget: int,
    trust_score: float,
    wcag_violations: int,
    hitl_rejected: bool = False,
) -> RewardComponents:
    r_task = 1.0 if task_completed else 0.0

    if time_budget_ms <= 0:
        r_time = 0.0
    else:
        r_time = -min(1.0, completion_time_ms / time_budget_ms)

    if error_budget <= 0:
        r_error = 0.0
    else:
        r_error = -min(1.0, error_count / error_budget)

    r_trust = max(0.0, min(1.0, trust_score))

    r_base = (
        REWARD_WEIGHTS["task"] * r_task
        + REWARD_WEIGHTS["time"] * r_time
        + REWARD_WEIGHTS["error"] * r_error
        + REWARD_WEIGHTS["trust"] * r_trust
    )

    p_wcag = WCAG_PENALTY_LAMBDA * float(wcag_violations)
    hitl_penalty = HITL_REJECT_PENALTY if hitl_rejected else 0.0
    r_final = r_base - p_wcag + hitl_penalty

    return RewardComponents(
        r_task=r_task,
        r_time=r_time,
        r_error=r_error,
        r_trust=r_trust,
        p_wcag=p_wcag,
        r_base=r_base,
        r_final=r_final,
        hitl_penalty=hitl_penalty,
    )
