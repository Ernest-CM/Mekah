import pytest
from app.core.reward import compute_reward
from app.config import REWARD_WEIGHTS, WCAG_PENALTY_LAMBDA, HITL_REJECT_PENALTY


def test_perfect_outcome_max_base_reward():
    r = compute_reward(
        task_completed=True,
        completion_time_ms=0.0,
        time_budget_ms=60000.0,
        error_count=0,
        error_budget=4,
        trust_score=1.0,
        wcag_violations=0,
    )
    expected_base = (
        REWARD_WEIGHTS["task"] * 1
        + REWARD_WEIGHTS["time"] * 0
        + REWARD_WEIGHTS["error"] * 0
        + REWARD_WEIGHTS["trust"] * 1
    )
    assert r.r_base == pytest.approx(expected_base)
    assert r.r_final == pytest.approx(expected_base)


def test_failure_outcome_minimum_reward():
    r = compute_reward(
        task_completed=False,
        completion_time_ms=120000.0,
        time_budget_ms=60000.0,
        error_count=10,
        error_budget=4,
        trust_score=0.0,
        wcag_violations=0,
    )
    assert r.r_task == 0.0
    assert r.r_time == -1.0
    assert r.r_error == -1.0
    assert r.r_trust == 0.0


def test_wcag_penalty_subtracted():
    r = compute_reward(
        task_completed=True,
        completion_time_ms=10000.0,
        time_budget_ms=60000.0,
        error_count=0,
        error_budget=4,
        trust_score=0.8,
        wcag_violations=2,
    )
    assert r.p_wcag == pytest.approx(2.0 * WCAG_PENALTY_LAMBDA)
    assert r.r_final == pytest.approx(r.r_base - r.p_wcag)


def test_hitl_rejection_adds_negative_bonus():
    r = compute_reward(
        task_completed=True,
        completion_time_ms=5000.0,
        time_budget_ms=60000.0,
        error_count=0,
        error_budget=4,
        trust_score=0.7,
        wcag_violations=0,
        hitl_rejected=True,
    )
    assert r.hitl_penalty == HITL_REJECT_PENALTY
    assert r.r_final == pytest.approx(r.r_base + HITL_REJECT_PENALTY)


def test_trust_score_clipped_to_unit_interval():
    r = compute_reward(
        task_completed=True,
        completion_time_ms=0.0,
        time_budget_ms=60000.0,
        error_count=0,
        error_budget=4,
        trust_score=2.0,  # out of range
        wcag_violations=0,
    )
    assert r.r_trust == 1.0


def test_zero_budgets_neutralize_components():
    r = compute_reward(
        task_completed=True,
        completion_time_ms=10000.0,
        time_budget_ms=0.0,
        error_count=3,
        error_budget=0,
        trust_score=0.5,
        wcag_violations=0,
    )
    assert r.r_time == 0.0
    assert r.r_error == 0.0
