"""Synthetic environment that turns (persona, action, ui_state) into the reward
components we need to call `compute_reward`.

This is the offline twin of what the real frontend would measure: completion
time, error count, trust feedback. Personas have *preferred* actions: when an
action matches, completion time goes down, errors go down, and trust goes up.
"""
from __future__ import annotations
import numpy as np

from ..core.actions import get_action
from ..core.wcag import simulate_state, validate_state, Severity
from ..core.reward import compute_reward
from .personas import Persona


TIME_BUDGET_MS = 15_000
ERROR_BUDGET = 4


def step(
    persona: Persona,
    action_id: str,
    current_ui_state: dict,
    rng: np.random.Generator,
    hitl_rejected: bool = False,
) -> tuple[dict, dict]:
    """Apply `action_id`, simulate the new UI state, draw an outcome,
    and return (next_ui_state, reward_record).

    reward_record contains the components plus task_completed, completion_time_ms,
    error_count, trust_score, wcag_violations.
    """
    action = get_action(action_id)
    next_state = simulate_state(current_ui_state, action)
    violations = validate_state(next_state, persona.profile)
    hard_failures = sum(1 for v in violations if v.severity == Severity.FAIL)

    fit = 1.0 if action_id in persona.preferred_actions else 0.0
    affinity = 0.5 + 0.5 * fit

    base_time = persona.base_completion_time_ms
    completion_time_ms = float(
        np.clip(rng.normal(base_time * (1.4 - 0.5 * fit), base_time * 0.15), 1000, TIME_BUDGET_MS)
    )

    base_err = persona.base_error_rate * (1.4 - 0.7 * fit)
    error_count = int(rng.poisson(base_err * 4))

    trust_score = float(
        np.clip(
            rng.normal(persona.base_trust_score * affinity + 0.15 * fit, 0.08),
            0.0,
            1.0,
        )
    )

    task_completed = (error_count <= ERROR_BUDGET) and (completion_time_ms < TIME_BUDGET_MS)

    components = compute_reward(
        task_completed=task_completed,
        completion_time_ms=completion_time_ms,
        time_budget_ms=TIME_BUDGET_MS,
        error_count=error_count,
        error_budget=ERROR_BUDGET,
        trust_score=trust_score,
        wcag_violations=hard_failures,
        hitl_rejected=hitl_rejected,
    )

    return next_state, {
        "components": components,
        "task_completed": task_completed,
        "completion_time_ms": completion_time_ms,
        "error_count": error_count,
        "trust_score": trust_score,
        "wcag_violations": hard_failures,
        "fit": fit,
    }
