"""Baseline adaptation policies for A/B comparison (revised.md §7.3).

Each baseline implements `select(x, allowed_idx) -> arm_idx` so the experiment
runner can plug them in interchangeably with LinUCB.
"""
from __future__ import annotations
import numpy as np
from ..core.actions import ACTIONS, ACTION_INDEX
from ..core.features import FEATURE_NAMES


class StaticBaseline:
    """No adaptation: always pick A6 (no change). Models the legacy interface."""

    name = "static"

    def select(self, x: np.ndarray, allowed_idx: list[int]) -> tuple[int, float]:
        a6 = ACTION_INDEX["A6"]
        if a6 in allowed_idx:
            return a6, 1.0
        return allowed_idx[0], 1.0

    def update(self, arm_idx: int, x: np.ndarray, reward: float) -> None:
        pass


class RandomBaseline:
    """Uniform random selection over the allowed set."""

    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def select(self, x: np.ndarray, allowed_idx: list[int]) -> tuple[int, float]:
        return int(self.rng.choice(allowed_idx)), 1.0 / len(allowed_idx)

    def update(self, arm_idx: int, x: np.ndarray, reward: float) -> None:
        pass


class RuleBasedBaseline:
    """Hand-coded mapping from user-profile features to a single action.

    Mirrors the rule-based adaptive interfaces critiqued in Ch. 2 §2.4 of the
    project document — simple if/else logic that doesn't learn.
    """

    name = "rule_based"

    def select(self, x: np.ndarray, allowed_idx: list[int]) -> tuple[int, float]:
        i_visual = FEATURE_NAMES.index("visual_pref")
        i_motor = FEATURE_NAMES.index("motor_pref")
        i_cog = FEATURE_NAMES.index("cognitive_pref")
        i_motion_warn = FEATURE_NAMES.index("wcag_risk_n")

        if x[i_visual] >= 0.7:
            chosen = "A2"
        elif x[i_motor] >= 0.7:
            chosen = "A4"
        elif x[i_cog] >= 0.7:
            chosen = "A3"
        elif x[i_motion_warn] >= 0.5:
            chosen = "A5"
        else:
            chosen = "A6"

        idx = ACTION_INDEX[chosen]
        if idx in allowed_idx:
            return idx, 1.0
        # If the rule's choice was filtered out by the safety shield, fall back
        # to A6 if allowed, else first allowed.
        a6 = ACTION_INDEX["A6"]
        return (a6 if a6 in allowed_idx else allowed_idx[0]), 1.0

    def update(self, arm_idx: int, x: np.ndarray, reward: float) -> None:
        pass


class LinUCBPolicy:
    """Wraps the LinUCB learner so it has the same interface as baselines."""

    name = "linucb"

    def __init__(self, model):
        self.model = model

    def select(self, x: np.ndarray, allowed_idx: list[int]) -> tuple[int, float]:
        idx, conf, _scores = self.model.select(x, allowed_idx)
        return idx, conf

    def update(self, arm_idx: int, x: np.ndarray, reward: float) -> None:
        self.model.update(arm_idx, x, reward)
