"""
LinUCB Diagnostic Script — Track 1 investigation.

Runs the full phased experiment and prints:
  1. Per-arm pull counts for each phase
  2. Per-persona arm selection (Phase C frozen test)
  3. Per-persona reward breakdown (fit vs non-fit)
  4. UCB score spread at start and end of learning
  5. Alpha sweep: reward improvement vs static across alpha values
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from collections import defaultdict
from app.core.actions import ACTIONS, ACTION_INDEX, NUM_ACTIONS
from app.core.features import FEATURE_DIM, build_context_vector, FEATURE_NAMES
from app.core.linucb import LinUCB
from app.core.wcag import filter_allowed
from app.core.reward import compute_reward
from app.eval.baselines import LinUCBPolicy, StaticBaseline, RuleBasedBaseline
from app.eval.environment import step
from app.eval.personas import PERSONAS, sample_session_behavior, context_for
from app.config import LINUCB_ALPHA


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def run_phased(alpha: float, seed: int = 42, warmup=60, learning=240, test=120):
    """Full phased run returning (phase_a, phase_b, phase_c) records."""
    rng = np.random.default_rng(seed)
    learner = LinUCB(n_arms=NUM_ACTIONS, n_features=FEATURE_DIM, alpha=alpha)
    policy = LinUCBPolicy(learner)

    records = {"warmup": [], "learning": [], "test": []}
    for phase, n_eps, learn in [
        ("warmup",   warmup,   True),
        ("learning", learning, True),
        ("test",     test,     False),
    ]:
        for _ in range(n_eps):
            persona = PERSONAS[int(rng.integers(0, len(PERSONAS)))]
            ui_state = dict(persona.starting_state)
            behavior = sample_session_behavior(persona, rng)
            ctx = context_for(persona, behavior, ui_state)
            x = build_context_vector(ctx)

            allowed = filter_allowed(ui_state, persona.profile, [a.id for a in ACTIONS])
            allowed_idx = [ACTION_INDEX[a] for a in allowed]
            arm_idx, conf = policy.select(x, allowed_idx)
            arm_id = ACTIONS[arm_idx].id
            _, outcome = step(persona, arm_id, ui_state, rng)
            reward = outcome["components"].r_final
            if learn:
                policy.update(arm_idx, x, reward)

            records[phase].append({
                "persona": persona.id,
                "arm": arm_id,
                "reward": reward,
                "trust": outcome["trust_score"],
                "time_ms": outcome["completion_time_ms"],
                "fit": outcome["fit"],
                "conf": conf,
            })

    return records, learner


def static_test_reward(seed: int = 42, warmup=60, learning=240, test=120) -> float:
    """Mean reward for static baseline in frozen phase."""
    rng = np.random.default_rng(seed)
    policy = StaticBaseline()
    rewards = []
    for _ in range(warmup + learning):  # burn through same RNG state
        persona = PERSONAS[int(rng.integers(0, len(PERSONAS)))]
        ui_state = dict(persona.starting_state)
        behavior = sample_session_behavior(persona, rng)
        _ = context_for(persona, behavior, ui_state)
    for _ in range(test):
        persona = PERSONAS[int(rng.integers(0, len(PERSONAS)))]
        ui_state = dict(persona.starting_state)
        behavior = sample_session_behavior(persona, rng)
        ctx = context_for(persona, behavior, ui_state)
        x = build_context_vector(ctx)
        allowed = filter_allowed(ui_state, persona.profile, [a.id for a in ACTIONS])
        allowed_idx = [ACTION_INDEX[a] for a in allowed]
        arm_idx, _ = policy.select(x, allowed_idx)
        arm_id = ACTIONS[arm_idx].id
        _, outcome = step(persona, arm_id, ui_state, rng)
        rewards.append(outcome["components"].r_final)
    return float(np.mean(rewards))


# ─────────────────────────────────────────────
# Section 1: Per-arm pull counts
# ─────────────────────────────────────────────

def section_arm_counts(records):
    print("\n" + "═" * 60)
    print("1. Per-arm pull counts per phase")
    print("═" * 60)
    for phase in ("warmup", "learning", "test"):
        counts = defaultdict(int)
        for r in records[phase]:
            counts[r["arm"]] += 1
        total = len(records[phase])
        print(f"\n  {phase} ({total} eps):")
        for a in ACTIONS:
            pct = counts[a.id] / total * 100
            bar = "█" * int(pct / 2)
            print(f"    {a.id} ({a.label[:22]:<22}): {counts[a.id]:3d} ({pct:5.1f}%)  {bar}")


# ─────────────────────────────────────────────
# Section 2: Per-persona arm selection in Phase C
# ─────────────────────────────────────────────

def section_persona_arms(records):
    print("\n" + "═" * 60)
    print("2. Phase C arm selection by persona  (preferred action in [brackets])")
    print("═" * 60)
    persona_prefs = {p.id: p.preferred_actions for p in PERSONAS}
    by_persona = defaultdict(lambda: defaultdict(int))
    for r in records["test"]:
        by_persona[r["persona"]][r["arm"]] += 1

    for pid, prefs in persona_prefs.items():
        counts = by_persona[pid]
        total = sum(counts.values())
        if total == 0:
            continue
        print(f"\n  {pid} (prefers {prefs}):")
        for a in ACTIONS:
            mark = "←" if a.id in prefs else " "
            pct = counts[a.id] / total * 100 if total else 0
            print(f"    {a.id} {mark} {pct:5.1f}%")


# ─────────────────────────────────────────────
# Section 3: Reward signal analysis
# ─────────────────────────────────────────────

def section_reward_signal():
    print("\n" + "═" * 60)
    print("3. Reward signal: fit=1 vs fit=0 (100 samples per persona)")
    print("═" * 60)
    rng = np.random.default_rng(999)
    for persona in PERSONAS:
        fit_rewards, nofit_rewards = [], []
        for a in ACTIONS:
            for _ in range(100):
                ui = dict(persona.starting_state)
                _, out = step(persona, a.id, ui, rng)
                if out["fit"] == 1.0:
                    fit_rewards.append(out["components"].r_final)
                else:
                    nofit_rewards.append(out["components"].r_final)
        if fit_rewards and nofit_rewards:
            snr = abs(np.mean(fit_rewards) - np.mean(nofit_rewards)) / (np.std(nofit_rewards) + 1e-9)
            print(f"  {persona.id:<16}: fit={np.mean(fit_rewards):+.3f}±{np.std(fit_rewards):.3f}  "
                  f"no-fit={np.mean(nofit_rewards):+.3f}±{np.std(nofit_rewards):.3f}  "
                  f"SNR={snr:.2f}")


# ─────────────────────────────────────────────
# Section 4: UCB score spread
# ─────────────────────────────────────────────

def section_ucb_spread(learner: LinUCB):
    print("\n" + "═" * 60)
    print("4. UCB score spread on trained model (per persona)")
    print("═" * 60)
    rng = np.random.default_rng(0)
    for persona in PERSONAS:
        ui = dict(persona.starting_state)
        behavior = sample_session_behavior(persona, rng)
        ctx = context_for(persona, behavior, ui)
        x = build_context_vector(ctx)
        scores = learner.score_all(x)
        best = ACTIONS[int(np.argmax(scores))].id
        prefs = [p.preferred_actions for p in PERSONAS if p.id == persona.id][0]
        correct = "✓" if best in prefs else "✗"
        score_str = "  ".join(f"{a.id}:{scores[i]:+.3f}" for i, a in enumerate(ACTIONS))
        print(f"  {persona.id:<16}: best={best} {correct}  [{score_str}]")


# ─────────────────────────────────────────────
# Section 5: Alpha sweep
# ─────────────────────────────────────────────

def section_alpha_sweep():
    print("\n" + "═" * 60)
    print("5. Alpha sweep — reward improvement vs static baseline")
    print("   (target: >= +15%)")
    print("═" * 60)

    # Run static once with matched RNG
    static_r = static_test_reward(seed=42)
    print(f"\n  Static baseline test reward: {static_r:+.4f}")
    print()
    print(f"  {'alpha':>8}  {'LinUCB test reward':>20}  {'improvement':>14}  {'target met':>12}")
    print(f"  {'-'*8}  {'-'*20}  {'-'*14}  {'-'*12}")

    best_alpha, best_improvement = None, -999.0
    alphas = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.00, 1.50]
    for alpha in alphas:
        records, _ = run_phased(alpha=alpha, seed=42)
        test_r = float(np.mean([r["reward"] for r in records["test"]]))
        improvement = (test_r - static_r) / abs(static_r) if static_r != 0 else float("inf")
        met = "✓ MET" if improvement >= 0.15 else "✗"
        print(f"  {alpha:>8.2f}  {test_r:>+20.4f}  {improvement:>+13.2%}  {met:>12}")
        if improvement > best_improvement:
            best_improvement = improvement
            best_alpha = alpha

    print(f"\n  Best alpha: {best_alpha}  improvement={best_improvement:+.2%}")
    return best_alpha


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Running phased experiment (alpha=1.0, original config) …")
    records, learner = run_phased(alpha=LINUCB_ALPHA)

    section_arm_counts(records)
    section_persona_arms(records)
    section_reward_signal()
    section_ucb_spread(learner)
    best_alpha = section_alpha_sweep()

    print("\n" + "═" * 60)
    print("DIAGNOSIS COMPLETE")
    print(f"Recommended alpha: {best_alpha}")
    print("See sections above for root cause breakdown.")
    print("═" * 60)
