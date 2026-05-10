"""LinUCB contextual bandit (disjoint per-arm linear payoff).

For each arm a, maintain A_a = I + sum x x^T  and  b_a = sum r * x.
At decision time: theta_a = A_a^-1 b_a, score = theta_a . x + alpha * sqrt(x^T A_a^-1 x).
Pick argmax; on update, accumulate (x, r) for the chosen arm.

Reference: Li et al. (2010), "A Contextual-Bandit Approach to Personalized News
Article Recommendation."
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
import numpy as np


@dataclass
class ArmState:
    A: np.ndarray
    b: np.ndarray
    n_pulls: int = 0
    cumulative_reward: float = 0.0


@dataclass
class LinUCB:
    n_arms: int
    n_features: int
    alpha: float = 1.0
    arms: list[ArmState] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.arms:
            self.arms = [
                ArmState(A=np.eye(self.n_features), b=np.zeros(self.n_features))
                for _ in range(self.n_arms)
            ]

    def score_all(self, x: np.ndarray) -> np.ndarray:
        x = x.reshape(-1)
        scores = np.empty(self.n_arms, dtype=np.float64)
        for i, arm in enumerate(self.arms):
            A_inv = np.linalg.inv(arm.A)
            theta = A_inv @ arm.b
            mean = float(theta @ x)
            ucb = self.alpha * float(np.sqrt(max(x @ A_inv @ x, 0.0)))
            scores[i] = mean + ucb
        return scores

    def select(
        self,
        x: np.ndarray,
        allowed: Iterable[int] | None = None,
    ) -> tuple[int, float, np.ndarray]:
        scores = self.score_all(x)
        mask = np.full(self.n_arms, -np.inf)
        if allowed is None:
            allowed_set = range(self.n_arms)
        else:
            allowed_set = list(allowed)
            if not allowed_set:
                raise ValueError("LinUCB.select: allowed set is empty")
        for i in allowed_set:
            mask[i] = scores[i]
        idx = int(np.argmax(mask))
        confidence = self._confidence_from_scores(scores, idx)
        return idx, confidence, scores

    @staticmethod
    def _confidence_from_scores(scores: np.ndarray, idx: int) -> float:
        s = scores - scores.max()
        exp = np.exp(s)
        probs = exp / exp.sum()
        return float(probs[idx])

    def update(self, arm_idx: int, x: np.ndarray, reward: float) -> None:
        x = x.reshape(-1)
        arm = self.arms[arm_idx]
        arm.A = arm.A + np.outer(x, x)
        arm.b = arm.b + reward * x
        arm.n_pulls += 1
        arm.cumulative_reward += reward

    def snapshot(self) -> dict:
        return {
            "n_arms": self.n_arms,
            "n_features": self.n_features,
            "alpha": self.alpha,
            "arms": [
                {
                    "A": arm.A.tolist(),
                    "b": arm.b.tolist(),
                    "n_pulls": arm.n_pulls,
                    "cumulative_reward": arm.cumulative_reward,
                }
                for arm in self.arms
            ],
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "LinUCB":
        arms = [
            ArmState(
                A=np.array(a["A"], dtype=np.float64),
                b=np.array(a["b"], dtype=np.float64),
                n_pulls=int(a.get("n_pulls", 0)),
                cumulative_reward=float(a.get("cumulative_reward", 0.0)),
            )
            for a in data["arms"]
        ]
        return cls(
            n_arms=int(data["n_arms"]),
            n_features=int(data["n_features"]),
            alpha=float(data.get("alpha", 1.0)),
            arms=arms,
        )
