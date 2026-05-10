"""Phased online evaluation runner (revised.md §7.1-7.4).

Replaces Chapter 3 §3.11's invalid 80:20 split with the methodologically
correct sequence:

  Phase A : warm-up         - safe defaults, limited exploration
  Phase B : online learning - LinUCB updates after every event
  Phase C : frozen test     - alpha=0, no updates, A/B vs baselines

For each policy we run identical persona schedules driven by the same RNG seed
so the comparison is matched.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import numpy as np

from ..config import LINUCB_ALPHA
from ..core.actions import ACTIONS, ACTION_INDEX
from ..core.features import FEATURE_DIM, build_context_vector
from ..core.linucb import LinUCB
from ..core.wcag import filter_allowed
from .baselines import LinUCBPolicy, RandomBaseline, RuleBasedBaseline, StaticBaseline
from .environment import step
from .personas import PERSONAS, Persona, sample_session_behavior, context_for
from .stats import two_proportion_z, mann_whitney, confidence_interval, TestResult


@dataclass
class EpisodeRecord:
    persona: str
    arm: str
    fit: float
    reward: float
    completion_time_ms: float
    error_count: int
    trust_score: float
    task_completed: bool
    wcag_violations: int


@dataclass
class PolicyRun:
    policy_name: str
    phase_a: list[EpisodeRecord] = field(default_factory=list)
    phase_b: list[EpisodeRecord] = field(default_factory=list)
    phase_c: list[EpisodeRecord] = field(default_factory=list)

    @staticmethod
    def _summary(records: list[EpisodeRecord]) -> dict[str, Any]:
        if not records:
            return {}
        rewards = [r.reward for r in records]
        times = [r.completion_time_ms for r in records]
        trust = [r.trust_score for r in records]
        completed = sum(1 for r in records if r.task_completed)
        compliant = sum(1 for r in records if r.wcag_violations == 0)

        mean_r, lo_r, hi_r = confidence_interval(rewards)
        return {
            "n": len(records),
            "mean_reward": mean_r,
            "reward_ci_95": [lo_r, hi_r],
            "median_completion_ms": float(np.median(times)),
            "mean_trust": float(np.mean(trust)),
            "completion_rate": completed / len(records),
            "compliance_rate": compliant / len(records),
        }

    def summarize(self) -> dict[str, Any]:
        return {
            "policy": self.policy_name,
            "phase_a_warmup": self._summary(self.phase_a),
            "phase_b_learning": self._summary(self.phase_b),
            "phase_c_frozen_test": self._summary(self.phase_c),
        }


@dataclass
class ExperimentConfig:
    warmup_episodes: int = 60
    learning_episodes: int = 240
    test_episodes: int = 120
    seed: int = 42


class ExperimentRunner:
    def __init__(self, cfg: ExperimentConfig | None = None):
        self.cfg = cfg or ExperimentConfig()

    def _persona_schedule(self, n: int, rng: np.random.Generator) -> list[Persona]:
        return [PERSONAS[int(rng.integers(0, len(PERSONAS)))] for _ in range(n)]

    def _run_phase(
        self,
        policy,
        schedule: list[Persona],
        rng: np.random.Generator,
        learn: bool,
    ) -> list[EpisodeRecord]:
        out: list[EpisodeRecord] = []
        for persona in schedule:
            ui_state = dict(persona.starting_state)
            behavior = sample_session_behavior(persona, rng)
            ctx = context_for(persona, behavior, ui_state)
            x = build_context_vector(ctx)

            allowed = filter_allowed(
                ui_state, persona.profile, [a.id for a in ACTIONS]
            )
            allowed_idx = [ACTION_INDEX[a] for a in allowed]

            arm_idx, _conf = policy.select(x, allowed_idx)
            arm_id = ACTIONS[arm_idx].id

            _next_state, outcome = step(persona, arm_id, ui_state, rng)
            reward = outcome["components"].r_final

            if learn:
                policy.update(arm_idx, x, reward)

            out.append(
                EpisodeRecord(
                    persona=persona.id,
                    arm=arm_id,
                    fit=outcome["fit"],
                    reward=reward,
                    completion_time_ms=outcome["completion_time_ms"],
                    error_count=outcome["error_count"],
                    trust_score=outcome["trust_score"],
                    task_completed=outcome["task_completed"],
                    wcag_violations=outcome["wcag_violations"],
                )
            )
        return out

    def run_policy(self, policy, label: str, rng_seed: int) -> PolicyRun:
        rng = np.random.default_rng(rng_seed)
        warmup_sched = self._persona_schedule(self.cfg.warmup_episodes, rng)
        learning_sched = self._persona_schedule(self.cfg.learning_episodes, rng)
        test_sched = self._persona_schedule(self.cfg.test_episodes, rng)

        run = PolicyRun(policy_name=label)
        run.phase_a = self._run_phase(policy, warmup_sched, rng, learn=True)
        run.phase_b = self._run_phase(policy, learning_sched, rng, learn=True)
        run.phase_c = self._run_phase(policy, test_sched, rng, learn=False)
        return run

    def run_all(self) -> dict[str, Any]:
        learner = LinUCB(n_arms=len(ACTIONS), n_features=FEATURE_DIM, alpha=LINUCB_ALPHA)
        runs = [
            self.run_policy(LinUCBPolicy(learner), "linucb", self.cfg.seed),
            self.run_policy(StaticBaseline(), "static", self.cfg.seed),
            self.run_policy(RuleBasedBaseline(), "rule_based", self.cfg.seed),
            self.run_policy(RandomBaseline(seed=self.cfg.seed), "random", self.cfg.seed),
        ]
        return self._compose_report(runs)

    @staticmethod
    def _compose_report(runs: list[PolicyRun]) -> dict[str, Any]:
        summaries = {r.policy_name: r.summarize() for r in runs}
        by_name = {r.policy_name: r for r in runs}

        def test_block(against: str) -> dict[str, Any]:
            linucb_test = by_name["linucb"].phase_c
            other_test = by_name[against].phase_c

            n_l = len(linucb_test)
            n_o = len(other_test)
            comp_l = sum(1 for r in linucb_test if r.wcag_violations == 0)
            comp_o = sum(1 for r in other_test if r.wcag_violations == 0)

            tests: dict[str, TestResult] = {
                "compliance_rate": two_proportion_z(comp_l, n_l, comp_o, n_o),
                "completion_time_ms": mann_whitney(
                    [r.completion_time_ms for r in linucb_test],
                    [r.completion_time_ms for r in other_test],
                    "completion_time_ms",
                ),
                "trust_score": mann_whitney(
                    [r.trust_score for r in linucb_test],
                    [r.trust_score for r in other_test],
                    "trust_score",
                ),
                "reward": mann_whitney(
                    [r.reward for r in linucb_test],
                    [r.reward for r in other_test],
                    "reward",
                ),
            }
            return {
                k: {
                    "name": v.name,
                    "statistic": v.statistic,
                    "p_value": v.p_value,
                    "effect_size": v.effect_size,
                    "interpretation": v.interpretation,
                }
                for k, v in tests.items()
            }

        report = {
            "summaries": summaries,
            "linucb_vs_static": test_block("static"),
            "linucb_vs_rule_based": test_block("rule_based"),
            "linucb_vs_random": test_block("random"),
        }

        # Headline KPIs against revised.md §3 targets
        l_test = by_name["linucb"].phase_c
        s_test = by_name["static"].phase_c
        l_reward = float(np.mean([r.reward for r in l_test])) if l_test else 0.0
        s_reward = float(np.mean([r.reward for r in s_test])) if s_test else 0.0
        improvement = (l_reward - s_reward) / abs(s_reward) if s_reward != 0 else float("inf")
        compliance = sum(1 for r in l_test if r.wcag_violations == 0) / len(l_test) if l_test else 0.0

        report["targets"] = {
            "reward_improvement_vs_static": improvement,
            "reward_improvement_target": 0.15,
            "reward_improvement_met": improvement >= 0.15,
            "compliance_rate": compliance,
            "compliance_target": 0.98,
            "compliance_met": compliance >= 0.98,
        }
        return report


def render_report(report: dict[str, Any]) -> str:
    lines = ["", "=" * 72, "Phased Online Evaluation Report (revised.md §7)", "=" * 72]

    for name, summary in report["summaries"].items():
        lines.append(f"\n--- Policy: {name} ---")
        for phase in ("phase_a_warmup", "phase_b_learning", "phase_c_frozen_test"):
            s = summary[phase]
            if not s:
                continue
            lines.append(
                f"  {phase}: n={s['n']}  reward={s['mean_reward']:+.3f} "
                f"(95% CI [{s['reward_ci_95'][0]:+.3f}, {s['reward_ci_95'][1]:+.3f}])  "
                f"med_time={s['median_completion_ms']:.0f}ms  "
                f"trust={s['mean_trust']:.2f}  "
                f"compliance={s['compliance_rate']:.3f}  "
                f"completion={s['completion_rate']:.3f}"
            )

    for block in ("linucb_vs_static", "linucb_vs_rule_based", "linucb_vs_random"):
        lines.append(f"\n--- Statistical tests: {block} ---")
        for metric, payload in report[block].items():
            lines.append(
                f"  {metric}: {payload['name']}  stat={payload['statistic']:+.3f} "
                f"p={payload['p_value']:.4f}  effect={payload['effect_size']:+.3f}"
            )
            lines.append(f"    {payload['interpretation']}")

    t = report["targets"]
    lines.append("\n--- Headline targets (revised.md §3) ---")
    lines.append(
        f"  Reward improvement vs static: {t['reward_improvement_vs_static']:+.2%}  "
        f"(target {t['reward_improvement_target']:+.0%}, "
        f"{'MET' if t['reward_improvement_met'] else 'NOT MET'})"
    )
    lines.append(
        f"  WCAG compliance rate:        {t['compliance_rate']:.3%}  "
        f"(target {t['compliance_target']:.0%}, "
        f"{'MET' if t['compliance_met'] else 'NOT MET'})"
    )

    return "\n".join(lines)


def main() -> None:
    cfg = ExperimentConfig()
    runner = ExperimentRunner(cfg)
    report = runner.run_all()
    print(render_report(report))

    out_path = "experiment_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()
