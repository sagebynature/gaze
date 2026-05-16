import pytest

from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
    manual_activation_allowed,
)


def test_manual_activation_is_disabled_by_default() -> None:
    readiness = GazeReadiness(
        calibration=CalibrationStatus.READY,
        camera_available=True,
        tracker_available=True,
    )

    assert manual_activation_allowed(GazeFeatureFlags(), readiness) is False


def test_manual_activation_requires_tracking_readiness() -> None:
    flags = GazeFeatureFlags(gaze_enabled=True)

    assert manual_activation_allowed(flags, GazeReadiness()) is False


def test_manual_activation_allowed_when_enabled_and_ready() -> None:
    flags = GazeFeatureFlags(gaze_enabled=True)
    readiness = GazeReadiness(
        calibration=CalibrationStatus.READY,
        camera_available=True,
        tracker_available=True,
    )

    assert manual_activation_allowed(flags, readiness) is True


def test_auto_activation_stays_disabled_by_default() -> None:
    assert GazeFeatureFlags().auto_activate_enabled is False


def test_menu_state_defaults_are_safe_and_off() -> None:
    state = GazeAppState.default()

    assert state.flags.gaze_enabled is False
    assert state.menu_status == "off"
    assert state.current_target is None
    assert state.overlay_visible is False
    assert state.activation_blocked is True


def test_disable_panic_clears_target_hides_overlay_and_blocks_activation() -> None:
    state = GazeAppState.default().with_target(
        TargetSummary(app_name="Terminal", confidence=0.91, locked=True)
    )

    disabled = state.disable_panic()

    assert disabled.flags.gaze_enabled is False
    assert disabled.current_target is None
    assert disabled.overlay_visible is False
    assert disabled.activation_blocked is True
    assert disabled.last_status_message == "Gaze disabled"


def test_target_summary_has_no_window_title_field() -> None:
    target = TargetSummary(app_name="Safari", confidence=0.8, locked=True)

    assert not hasattr(target, "window_title")


def test_target_summary_rejects_obvious_title_like_labels_as_extra_guard() -> None:
    with pytest.raises(ValueError, match="app name only"):
        TargetSummary(app_name="Safari - Bank Statement.pdf", confidence=0.8, locked=True)


def test_with_target_keeps_overlay_hidden_when_gaze_is_disabled() -> None:
    state = GazeAppState.default().with_target(
        TargetSummary(app_name="Terminal", confidence=0.91, locked=True)
    )

    assert state.current_target is not None
    assert state.overlay_visible is False
    assert state.activation_blocked is True
