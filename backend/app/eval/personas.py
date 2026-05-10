"""Synthetic user personas for offline evaluation (revised.md §7.1).

Each persona has a profile, a set of preferences over UI dimensions, and a
sampling distribution for session behavior. They are not 'real' users — they
are deterministic-ish stand-ins drawn from typical accessibility archetypes
described in Ch. 2 (low vision, motor impairment, cognitive load, etc.).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
import numpy as np


@dataclass
class Persona:
    id: str
    label: str
    profile: dict
    preferred_actions: list[str]
    """Action IDs (A1..A6) this persona BENEFITS from. Choosing one gives a
    higher base reward; choosing a 'wrong' action gives a smaller one."""

    base_completion_time_ms: float = 8000.0
    base_error_rate: float = 0.10
    base_trust_score: float = 0.7

    starting_state: dict = field(
        default_factory=lambda: {
            "font_scale": 1.0,
            "contrast_level": "normal",
            "density": "default",
            "theme": "light",
            "hit_target_min_px": 32,
            "reduced_motion": False,
        }
    )


PERSONAS: list[Persona] = [
    Persona(
        id="default",
        label="Default user",
        profile={
            "assistive_tech": False,
            "visual_pref": 0.0,
            "motor_pref": 0.0,
            "cognitive_pref": 0.0,
        },
        preferred_actions=["A6"],
        base_completion_time_ms=6000,
        base_error_rate=0.05,
        base_trust_score=0.75,
    ),
    Persona(
        id="low_vision",
        label="Low vision",
        profile={
            "assistive_tech": False,
            "visual_pref": 0.85,
            "motor_pref": 0.0,
            "cognitive_pref": 0.0,
            "vulnerable": True,
        },
        preferred_actions=["A1", "A2"],
        base_completion_time_ms=10000,
        base_error_rate=0.18,
        base_trust_score=0.6,
    ),
    Persona(
        id="motor",
        label="Motor impairment",
        profile={
            "assistive_tech": False,
            "visual_pref": 0.1,
            "motor_pref": 0.85,
            "cognitive_pref": 0.1,
            "vulnerable": True,
            "reduced_motion_preferred": True,
        },
        preferred_actions=["A4", "A5"],
        base_completion_time_ms=12000,
        base_error_rate=0.22,
        base_trust_score=0.55,
    ),
    Persona(
        id="cognitive",
        label="Cognitive accommodations",
        profile={
            "assistive_tech": False,
            "visual_pref": 0.2,
            "motor_pref": 0.2,
            "cognitive_pref": 0.85,
            "vulnerable": True,
            "reduced_motion_preferred": True,
        },
        preferred_actions=["A3", "A5"],
        base_completion_time_ms=14000,
        base_error_rate=0.25,
        base_trust_score=0.5,
    ),
    Persona(
        id="screen_reader",
        label="Screen reader user",
        profile={
            "assistive_tech": True,
            "visual_pref": 0.6,
            "motor_pref": 0.2,
            "cognitive_pref": 0.0,
            "vulnerable": True,
        },
        preferred_actions=["A2", "A6"],
        base_completion_time_ms=11000,
        base_error_rate=0.15,
        base_trust_score=0.65,
    ),
]

PERSONAS_BY_ID = {p.id: p for p in PERSONAS}


def sample_session_behavior(persona: Persona, rng: np.random.Generator, task_stage: int = 1, total_steps: int = 4) -> dict:
    """Draw a noisy realization of the persona's typical session signals."""
    return {
        "click_latency_ms": float(np.clip(rng.normal(persona.base_completion_time_ms / 8, 200), 100, 5000)),
        "error_count": int(rng.poisson(persona.base_error_rate * total_steps)),
        "scroll_depth": float(np.clip(rng.uniform(0.2, 0.9), 0, 1)),
        "task_stage": task_stage,
        "total_steps": total_steps,
    }


def context_for(persona: Persona, behavior: dict, ui_state: dict, risk_score: float = 0.0) -> dict:
    return {
        "user_profile": persona.profile,
        "session_behavior": behavior,
        "ui_state": ui_state,
        "a11y_diagnostics": {"risk_score": risk_score},
    }
