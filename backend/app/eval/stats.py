"""Statistical tests called out in revised.md §7.4.

- Compliance rate: two-proportion z-test
- Completion time: Mann-Whitney U (non-parametric)
- Trust score: Mann-Whitney U
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy import stats


@dataclass
class TestResult:
    name: str
    statistic: float
    p_value: float
    effect_size: float
    interpretation: str


def two_proportion_z(successes_a: int, n_a: int, successes_b: int, n_b: int) -> TestResult:
    """Two-sample test for proportions. H0: p_a == p_b."""
    if n_a == 0 or n_b == 0:
        return TestResult("z_proportions", 0.0, 1.0, 0.0, "insufficient samples")

    p_a = successes_a / n_a
    p_b = successes_b / n_b
    p_pool = (successes_a + successes_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return TestResult("z_proportions", 0.0, 1.0, 0.0, "no variance")
    z = (p_a - p_b) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    effect = p_a - p_b
    interp = (
        f"p_A={p_a:.3f}, p_B={p_b:.3f}, diff={effect:+.3f}, "
        f"{'significant' if p < 0.05 else 'not significant'} at alpha=0.05"
    )
    return TestResult("z_proportions", z, p, effect, interp)


def mann_whitney(a: list[float], b: list[float], label: str) -> TestResult:
    if len(a) < 2 or len(b) < 2:
        return TestResult(f"mann_whitney_{label}", 0.0, 1.0, 0.0, "insufficient samples")
    a_arr, b_arr = np.asarray(a), np.asarray(b)
    res = stats.mannwhitneyu(a_arr, b_arr, alternative="two-sided")
    # Rank-biserial effect size
    rb = 1 - (2 * res.statistic) / (len(a_arr) * len(b_arr))
    interp = (
        f"median_A={np.median(a_arr):.2f}, median_B={np.median(b_arr):.2f}, "
        f"rank_biserial={rb:+.3f}, "
        f"{'significant' if res.pvalue < 0.05 else 'not significant'} at alpha=0.05"
    )
    return TestResult(f"mann_whitney_{label}", float(res.statistic), float(res.pvalue), float(rb), interp)


def confidence_interval(values: list[float], confidence: float = 0.95) -> tuple[float, float, float]:
    """Return (mean, lower, upper) for a 95% CI assuming normal sampling distribution."""
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    if len(arr) < 2:
        return mean, mean, mean
    sem = float(stats.sem(arr))
    h = sem * stats.t.ppf((1 + confidence) / 2.0, len(arr) - 1)
    return mean, mean - h, mean + h
