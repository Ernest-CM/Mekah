"""Build the context vector x_t from raw client telemetry.

Layout (revised.md §4.2):
  user profile      : assistive_tech, visual_pref, motor_pref, cognitive_pref
  session behavior  : click_latency_n, error_rate_n, scroll_depth_n, task_stage_n
  ui environment    : font_scale_n, contrast_level_n, density_n, theme_dark
  a11y diagnostics  : wcag_risk_n
  bias              : 1.0
"""
from __future__ import annotations
from typing import Any
import numpy as np

FEATURE_NAMES = [
    "assistive_tech",
    "visual_pref",
    "motor_pref",
    "cognitive_pref",
    "click_latency_n",
    "error_rate_n",
    "scroll_depth_n",
    "task_stage_n",
    "font_scale_n",
    "contrast_level_n",
    "density_n",
    "theme_dark",
    "wcag_risk_n",
    "bias",
]
FEATURE_DIM = len(FEATURE_NAMES)

_CONTRAST_MAP = {"low": 0.0, "normal": 0.33, "high": 0.66, "max": 1.0}
_DENSITY_MAP = {"compact": 0.0, "default": 0.5, "comfortable": 1.0}


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def build_context_vector(features: dict[str, Any]) -> np.ndarray:
    """Project raw telemetry into a normalized [0,1] feature vector.

    Missing fields default to 0 (neutral). Numeric inputs are clamped to [0,1]
    after light normalization so LinUCB sees a stable, bounded context.
    """
    profile = features.get("user_profile", {}) or {}
    session = features.get("session_behavior", {}) or {}
    ui = features.get("ui_state", {}) or {}
    diag = features.get("a11y_diagnostics", {}) or {}

    click_latency_ms = float(session.get("click_latency_ms", 0) or 0)
    error_count = float(session.get("error_count", 0) or 0)
    scroll_depth = float(session.get("scroll_depth", 0) or 0)
    task_stage = float(session.get("task_stage", 0) or 0)
    total_steps = max(float(session.get("total_steps", 1) or 1), 1.0)

    font_scale = float(ui.get("font_scale", 1.0) or 1.0)
    contrast_level = ui.get("contrast_level", "normal") or "normal"
    density = ui.get("density", "default") or "default"
    theme = ui.get("theme", "light") or "light"

    wcag_risk = float(diag.get("risk_score", 0.0) or 0.0)

    vec = np.array(
        [
            1.0 if profile.get("assistive_tech") else 0.0,
            _clip01(float(profile.get("visual_pref", 0.0) or 0.0)),
            _clip01(float(profile.get("motor_pref", 0.0) or 0.0)),
            _clip01(float(profile.get("cognitive_pref", 0.0) or 0.0)),
            _clip01(click_latency_ms / 2000.0),
            _clip01(error_count / 10.0),
            _clip01(scroll_depth),
            _clip01(task_stage / total_steps),
            _clip01((font_scale - 0.75) / 0.75),
            _CONTRAST_MAP.get(contrast_level, 0.33),
            _DENSITY_MAP.get(density, 0.5),
            1.0 if theme == "dark" else 0.0,
            _clip01(wcag_risk),
            1.0,
        ],
        dtype=np.float64,
    )
    assert vec.shape[0] == FEATURE_DIM
    return vec
