"""Phased online evaluation entry point.

Usage:
  py -3.12 run_experiment.py [--warmup N] [--learning N] [--test N] [--seed N]

Writes a structured JSON report to experiment_report.json and prints a human
readable summary including headline KPIs against revised.md §3 targets.
"""
import argparse
from app.eval.runner import ExperimentConfig, ExperimentRunner, render_report
import json


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--warmup", type=int, default=60)
    p.add_argument("--learning", type=int, default=240)
    p.add_argument("--test", type=int, default=120)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=str, default="experiment_report.json")
    args = p.parse_args()

    cfg = ExperimentConfig(
        warmup_episodes=args.warmup,
        learning_episodes=args.learning,
        test_episodes=args.test,
        seed=args.seed,
    )
    runner = ExperimentRunner(cfg)
    report = runner.run_all()
    print(render_report(report))

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
