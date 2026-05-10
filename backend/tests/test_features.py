import numpy as np
from app.core.features import build_context_vector, FEATURE_DIM, FEATURE_NAMES


def test_vector_dimension_stable():
    v = build_context_vector({})
    assert v.shape == (FEATURE_DIM,)
    assert FEATURE_NAMES[-1] == "bias"
    assert v[-1] == 1.0


def test_assistive_tech_flag_propagates():
    v = build_context_vector({"user_profile": {"assistive_tech": True}})
    assert v[FEATURE_NAMES.index("assistive_tech")] == 1.0


def test_numeric_features_clamped_to_unit_range():
    v = build_context_vector(
        {
            "user_profile": {"visual_pref": 99.0, "motor_pref": -5.0},
            "session_behavior": {
                "click_latency_ms": 999_999,
                "error_count": 999,
                "scroll_depth": 5.0,
            },
            "a11y_diagnostics": {"risk_score": 50.0},
        }
    )
    for name in FEATURE_NAMES[:-1]:
        idx = FEATURE_NAMES.index(name)
        assert 0.0 <= v[idx] <= 1.0, f"feature {name} = {v[idx]}"


def test_theme_dark_indicator():
    v_light = build_context_vector({"ui_state": {"theme": "light"}})
    v_dark = build_context_vector({"ui_state": {"theme": "dark"}})
    idx = FEATURE_NAMES.index("theme_dark")
    assert v_light[idx] == 0.0
    assert v_dark[idx] == 1.0


def test_contrast_level_ordinal():
    levels = ["low", "normal", "high", "max"]
    idx = FEATURE_NAMES.index("contrast_level_n")
    values = [
        build_context_vector({"ui_state": {"contrast_level": level}})[idx]
        for level in levels
    ]
    assert values == sorted(values)
    assert values[0] == 0.0 and values[-1] == 1.0


def test_missing_subobjects_default_to_neutral():
    v = build_context_vector({})
    assert v[FEATURE_NAMES.index("assistive_tech")] == 0.0
    assert v[FEATURE_NAMES.index("error_rate_n")] == 0.0
