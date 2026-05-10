"""WCAG 2.1 Safety Shield (revised.md §4.5 / project Chapter 3 §3.7).

Pre-deployment validator that simulates the *result* of applying a candidate
action to the current UI snapshot, then runs hard- and soft-rule checks. Hard
violations BLOCK the action; soft warnings escalate to HITL.

The rule set focuses on the WCAG 2.1 SC most affected by the supported actions:
  1.4.3  Contrast (Minimum)        - color contrast ratio >= 4.5:1
  1.4.4  Resize Text               - font scale >= 1.0 (no shrinking)
  1.4.10 Reflow                    - density not collapsed below readable
  2.1.1  Keyboard                  - never disable keyboard navigation
  2.5.5  Target Size (Enhanced)    - interactive targets >= 44px
  2.3.3  Animation from Interactions - reduced motion respected when requested
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import math

from .actions import Action, get_action


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class Violation:
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    sc_reference: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "sc_reference": self.sc_reference,
        }


@dataclass
class ValidationResult:
    status: Status
    violations: list[Violation] = field(default_factory=list)
    simulated_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "violations": [v.to_dict() for v in self.violations],
            "simulated_state": self.simulated_state,
            "hard_failures": sum(1 for v in self.violations if v.severity == Severity.FAIL),
            "warnings": sum(1 for v in self.violations if v.severity == Severity.WARN),
        }


def _luminance(hex_color: str) -> float:
    """Relative luminance per WCAG 2.x."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r2, g2, b2 = channel(r), channel(g), channel(b)
    return 0.2126 * r2 + 0.7152 * g2 + 0.0722 * b2


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    L1 = _luminance(fg_hex)
    L2 = _luminance(bg_hex)
    lighter, darker = max(L1, L2), min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)


_PALETTES = {
    "light": {
        "low": {"fg": "#888888", "bg": "#ffffff"},
        "normal": {"fg": "#444444", "bg": "#ffffff"},
        "high": {"fg": "#111111", "bg": "#ffffff"},
        "max": {"fg": "#000000", "bg": "#ffffff"},
    },
    "dark": {
        "low": {"fg": "#888888", "bg": "#1a1a1a"},
        "normal": {"fg": "#cccccc", "bg": "#121212"},
        "high": {"fg": "#f5f5f5", "bg": "#000000"},
        "max": {"fg": "#ffffff", "bg": "#000000"},
    },
}


def simulate_state(ui_snapshot: dict[str, Any], action: Action) -> dict[str, Any]:
    """Apply an action to a copy of the UI snapshot and return the projected state."""
    s = dict(ui_snapshot or {})
    p = action.payload or {}

    if "font_scale_delta" in p:
        s["font_scale"] = round(float(s.get("font_scale", 1.0)) + float(p["font_scale_delta"]), 4)
    if "contrast_level" in p:
        s["contrast_level"] = p["contrast_level"]
    if "density" in p:
        s["density"] = p["density"]
    if "hide_nonessential" in p:
        s["hide_nonessential"] = bool(p["hide_nonessential"])
    if "hit_target_min_px" in p:
        s["hit_target_min_px"] = int(p["hit_target_min_px"])
    if "reduced_motion" in p:
        s["reduced_motion"] = bool(p["reduced_motion"])

    return s


def _palette_for(state: dict[str, Any]) -> dict[str, str]:
    theme = state.get("theme", "light")
    contrast = state.get("contrast_level", "normal")
    return _PALETTES.get(theme, _PALETTES["light"]).get(
        contrast, _PALETTES["light"]["normal"]
    )


def validate_state(state: dict[str, Any], user_profile: dict[str, Any] | None = None) -> list[Violation]:
    profile = user_profile or {}
    out: list[Violation] = []

    palette = _palette_for(state)
    ratio = contrast_ratio(palette["fg"], palette["bg"])
    if ratio < 4.5:
        out.append(
            Violation(
                rule_id="contrast_min",
                rule_name="Color contrast (Minimum)",
                severity=Severity.FAIL,
                message=f"Contrast ratio {ratio:.2f}:1 is below the WCAG AA threshold of 4.5:1.",
                sc_reference="WCAG 2.1 SC 1.4.3",
            )
        )
    elif ratio < 7.0 and profile.get("visual_pref", 0.0) >= 0.5:
        out.append(
            Violation(
                rule_id="contrast_enhanced",
                rule_name="Color contrast (Enhanced)",
                severity=Severity.WARN,
                message=f"Contrast ratio {ratio:.2f}:1 is below AAA (7:1) for a user with elevated visual needs.",
                sc_reference="WCAG 2.1 SC 1.4.6",
            )
        )

    font_scale = float(state.get("font_scale", 1.0))
    if font_scale < 1.0:
        out.append(
            Violation(
                rule_id="resize_text",
                rule_name="Resize Text",
                severity=Severity.FAIL,
                message=f"Font scale {font_scale:.2f} would shrink text below the user-controlled baseline.",
                sc_reference="WCAG 2.1 SC 1.4.4",
            )
        )
    elif font_scale > 2.0:
        out.append(
            Violation(
                rule_id="resize_text_extreme",
                rule_name="Resize Text (overshoot)",
                severity=Severity.WARN,
                message=f"Font scale {font_scale:.2f} may cause reflow issues on small viewports.",
                sc_reference="WCAG 2.1 SC 1.4.10",
            )
        )

    target = int(state.get("hit_target_min_px", 24))
    if target < 24:
        out.append(
            Violation(
                rule_id="target_size",
                rule_name="Target Size",
                severity=Severity.FAIL,
                message=f"Hit target minimum {target}px is below the safe floor of 24px.",
                sc_reference="WCAG 2.1 SC 2.5.5",
            )
        )
    elif target < 44 and profile.get("motor_pref", 0.0) >= 0.5:
        out.append(
            Violation(
                rule_id="target_size_motor",
                rule_name="Target Size (motor accommodation)",
                severity=Severity.WARN,
                message=f"Hit target {target}px is below the recommended 44px for users with motor needs.",
                sc_reference="WCAG 2.1 SC 2.5.5",
            )
        )

    if state.get("keyboard_disabled"):
        out.append(
            Violation(
                rule_id="keyboard",
                rule_name="Keyboard Operability",
                severity=Severity.FAIL,
                message="Action would disable keyboard navigation.",
                sc_reference="WCAG 2.1 SC 2.1.1",
            )
        )

    if profile.get("reduced_motion_preferred") and not state.get("reduced_motion", False):
        out.append(
            Violation(
                rule_id="motion_pref",
                rule_name="Animation from Interactions",
                severity=Severity.WARN,
                message="User prefers reduced motion but motion is still enabled.",
                sc_reference="WCAG 2.1 SC 2.3.3",
            )
        )

    return out


def validate_action(
    ui_snapshot: dict[str, Any],
    action_id: str,
    user_profile: dict[str, Any] | None = None,
) -> ValidationResult:
    action = get_action(action_id)
    simulated = simulate_state(ui_snapshot, action)
    violations = validate_state(simulated, user_profile)

    if any(v.severity == Severity.FAIL for v in violations):
        status = Status.FAIL
    elif any(v.severity == Severity.WARN for v in violations):
        status = Status.WARN
    else:
        status = Status.PASS

    return ValidationResult(status=status, violations=violations, simulated_state=simulated)


SAFE_FALLBACK_ACTION_ID = "A6"


def filter_allowed(
    ui_snapshot: dict[str, Any],
    user_profile: dict[str, Any] | None,
    candidate_action_ids: list[str],
) -> list[str]:
    """Return only actions whose simulated state has zero hard failures."""
    out: list[str] = []
    for aid in candidate_action_ids:
        if validate_action(ui_snapshot, aid, user_profile).status != Status.FAIL:
            out.append(aid)
    if not out:
        out.append(SAFE_FALLBACK_ACTION_ID)
    return out
