"""Smoke test for the phased experiment runner.

Verifies that the runner produces the structure revised.md §7 calls for, with
all four policies and statistical-test blocks populated.
"""
from app.eval.runner import ExperimentConfig, ExperimentRunner


def test_runner_produces_full_report():
    cfg = ExperimentConfig(warmup_episodes=20, learning_episodes=40, test_episodes=20, seed=11)
    runner = ExperimentRunner(cfg)
    report = runner.run_all()

    for name in ("linucb", "static", "rule_based", "random"):
        assert name in report["summaries"]
        s = report["summaries"][name]
        assert s["phase_a_warmup"]["n"] == 20
        assert s["phase_b_learning"]["n"] == 40
        assert s["phase_c_frozen_test"]["n"] == 20

    for cmp in ("linucb_vs_static", "linucb_vs_rule_based", "linucb_vs_random"):
        for metric in ("compliance_rate", "completion_time_ms", "trust_score", "reward"):
            assert metric in report[cmp]
            assert "p_value" in report[cmp][metric]

    targets = report["targets"]
    assert "compliance_rate" in targets
    assert 0.0 <= targets["compliance_rate"] <= 1.0
    assert "reward_improvement_vs_static" in targets


def test_linucb_learns_from_phase_a_to_c():
    """LinUCB's frozen-test mean reward should be at least as good as its
    warm-up mean — a sanity check that learning isn't actively hurting."""
    cfg = ExperimentConfig(warmup_episodes=40, learning_episodes=160, test_episodes=80, seed=23)
    runner = ExperimentRunner(cfg)
    report = runner.run_all()

    s = report["summaries"]["linucb"]
    a = s["phase_a_warmup"]["mean_reward"]
    c = s["phase_c_frozen_test"]["mean_reward"]
    assert c >= a - 0.05, f"learning regressed: warmup={a:.3f}, test={c:.3f}"
