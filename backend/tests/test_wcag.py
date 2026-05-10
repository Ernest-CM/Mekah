import pytest
from app.core import wcag
from app.core.wcag import (
    Status,
    Severity,
    contrast_ratio,
    validate_action,
    filter_allowed,
)


def test_contrast_ratio_known_pairs():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    # mid-grey on white is around 4.5:1
    ratio = contrast_ratio("#767676", "#ffffff")
    assert 4.4 < ratio < 4.7


def test_low_contrast_light_state_fails_on_no_change():
    """If the base state already violates WCAG, even A6 (no change) must FAIL."""
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "low",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(snapshot, "A6", user_profile={})
    assert result.status == Status.FAIL
    assert any(v.rule_id == "contrast_min" for v in result.violations)


def test_high_contrast_passes():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(snapshot, "A6", user_profile={})
    assert result.status == Status.PASS


def test_increase_contrast_action_recovers_low_contrast_state():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "low",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(snapshot, "A2", user_profile={})
    assert result.status in (Status.PASS, Status.WARN)
    assert all(v.severity != Severity.FAIL for v in result.violations)


def test_target_size_warn_for_motor_user():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    res_default = validate_action(snapshot, "A6", user_profile={"motor_pref": 0.0})
    res_motor = validate_action(snapshot, "A6", user_profile={"motor_pref": 0.9})
    assert res_default.status == Status.PASS
    assert res_motor.status == Status.WARN
    assert any(v.rule_id == "target_size_motor" for v in res_motor.violations)


def test_a4_increases_target_size():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(snapshot, "A4", user_profile={"motor_pref": 0.9})
    assert result.simulated_state["hit_target_min_px"] == 44
    assert result.status == Status.PASS


def test_filter_allowed_drops_hard_failures():
    """In a state where some actions hard-fail, filter_allowed must exclude them
    but always include at least the safe fallback A6."""
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    allowed = filter_allowed(snapshot, {}, ["A1", "A2", "A3", "A4", "A5", "A6"])
    assert "A6" in allowed
    assert len(allowed) >= 1


def test_reduced_motion_warn_when_user_prefers():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(
        snapshot, "A6", user_profile={"reduced_motion_preferred": True}
    )
    assert result.status == Status.WARN
    assert any(v.rule_id == "motion_pref" for v in result.violations)


def test_a5_clears_motion_warning():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    result = validate_action(
        snapshot, "A5", user_profile={"reduced_motion_preferred": True}
    )
    assert result.simulated_state["reduced_motion"] is True
    assert not any(v.rule_id == "motion_pref" for v in result.violations)


def test_simulate_state_does_not_mutate_input():
    snapshot = {
        "font_scale": 1.0,
        "contrast_level": "high",
        "density": "default",
        "theme": "light",
        "hit_target_min_px": 32,
        "reduced_motion": False,
    }
    snapshot_copy = dict(snapshot)
    wcag.simulate_state(snapshot, wcag.get_action("A1"))
    assert snapshot == snapshot_copy
