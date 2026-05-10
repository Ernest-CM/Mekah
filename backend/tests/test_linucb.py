import numpy as np
from app.core.linucb import LinUCB


def test_initial_state_uniform_scores():
    """With identity A and zero b, every arm has identical UCB on the same x."""
    policy = LinUCB(n_arms=3, n_features=4, alpha=1.0)
    x = np.array([0.5, 0.5, 0.5, 1.0])
    scores = policy.score_all(x)
    assert np.allclose(scores, scores[0])


def test_select_returns_valid_arm():
    policy = LinUCB(n_arms=4, n_features=3, alpha=1.0)
    x = np.array([0.2, 0.4, 1.0])
    arm, conf, scores = policy.select(x)
    assert 0 <= arm < 4
    assert 0.0 <= conf <= 1.0
    assert len(scores) == 4


def test_select_respects_allowed_set():
    policy = LinUCB(n_arms=5, n_features=2, alpha=1.0)
    x = np.array([0.5, 1.0])
    allowed = [1, 3]
    arm, _conf, _scores = policy.select(x, allowed=allowed)
    assert arm in allowed


def test_update_increases_chosen_arm_score_for_positive_reward():
    """After updating arm 0 with reward +1 on a context, the same context
    should score arm 0 above the un-pulled arms."""
    policy = LinUCB(n_arms=3, n_features=3, alpha=0.0)  # alpha=0 -> mean only
    x = np.array([0.7, 0.3, 1.0])
    policy.update(arm_idx=0, x=x, reward=1.0)
    scores = policy.score_all(x)
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_update_persists_pulls_and_cumulative_reward():
    policy = LinUCB(n_arms=2, n_features=2, alpha=1.0)
    x = np.array([1.0, 1.0])
    policy.update(0, x, 0.4)
    policy.update(0, x, 0.6)
    policy.update(1, x, 0.1)
    assert policy.arms[0].n_pulls == 2
    assert policy.arms[1].n_pulls == 1
    assert abs(policy.arms[0].cumulative_reward - 1.0) < 1e-9
    assert abs(policy.arms[1].cumulative_reward - 0.1) < 1e-9


def test_snapshot_round_trip_preserves_state():
    policy = LinUCB(n_arms=3, n_features=4, alpha=0.7)
    x = np.array([0.1, 0.5, 0.9, 1.0])
    policy.update(1, x, 0.5)
    policy.update(2, x, -0.2)

    snap = policy.snapshot()
    restored = LinUCB.from_snapshot(snap)

    s1 = policy.score_all(x)
    s2 = restored.score_all(x)
    assert np.allclose(s1, s2)
    assert restored.arms[1].n_pulls == 1
    assert restored.arms[2].n_pulls == 1


def test_alpha_increases_exploration_bonus():
    """A higher alpha should give un-pulled arms a larger UCB bonus, raising
    their score relative to a pulled arm with positive reward."""
    p_low = LinUCB(n_arms=3, n_features=2, alpha=0.1)
    p_high = LinUCB(n_arms=3, n_features=2, alpha=2.0)
    x = np.array([1.0, 1.0])

    p_low.update(0, x, 1.0)
    p_high.update(0, x, 1.0)

    s_low = p_low.score_all(x)
    s_high = p_high.score_all(x)

    # With alpha=0.1, pulled arm 0 should beat the unpulled arms.
    assert s_low[0] > s_low[1]
    # With alpha=2.0, exploration bonus on unpulled arms dominates the
    # exploitation lead of arm 0 — they should now score higher.
    assert s_high[1] > s_high[0]


def test_empty_allowed_set_raises():
    policy = LinUCB(n_arms=3, n_features=2)
    x = np.array([0.5, 0.5])
    try:
        policy.select(x, allowed=[])
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty allowed set")
