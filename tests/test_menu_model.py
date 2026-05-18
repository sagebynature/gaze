from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY
from gaze.ui.menu_model import menu_items_for_state


def test_menu_surfaces_auto_activate_only_as_restrained_opt_in_indicator() -> None:
    state = GazeAppState(
        flags=GazeFeatureFlags(auto_activate_enabled=True, auto_activate_debounce_ms=750),
        readiness=GazeReadiness(),
    )

    labels = [item.label for item in menu_items_for_state(state)]

    assert "Auto-activate: on after 750ms" in labels
    assert "Auto-activate now" not in labels


def test_default_hotkeys_match_design() -> None:
    assert MANUAL_ACTIVATE_HOTKEY == "cmd+g"
    assert GAZE_TOGGLE_HOTKEY == "option+cmd+g"


def test_menu_items_include_trust_controls_without_window_titles() -> None:
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.91, locked=True))

    items = menu_items_for_state(state)
    labels = [item.label for item in items]

    assert "Gaze: Ready" in labels
    assert "Target: Terminal" in labels
    assert "Calibration: Ready" in labels
    assert "Lock: locked" in labels
    assert "Manual activation: Cmd+G" in labels
    assert "Auto-activate: off" in labels
    assert "Disable Gaze" in labels
    assert "Target border: on" in labels
    assert "Recalibrate" in labels
    assert "Toggle Heatmap" not in labels
    assert all(not label.startswith("Confidence:") for label in labels)
    assert "Settings" in labels
    assert "Quit" in labels
    assert all(" - " not in label for label in labels)


def test_menu_copy_is_polished_and_avoids_internal_state_dump() -> None:
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True, target_border_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.DEGRADED,
            camera_available=True,
            tracker_available=True,
        ),
        last_status_message="Display layout changed; recalibrate recommended",
    )

    labels = [item.label for item in menu_items_for_state(state)]

    assert "Gaze: Degraded" in labels
    assert "Calibration: Degraded" in labels
    assert "Target: No target" in labels
    assert "Manual activation: Cmd+G" in labels
    assert "Target border: on" in labels
    assert "Auto-activate: off" in labels
    assert "Display layout changed; recalibrate recommended" in labels
    assert all(not label.startswith("Message:") for label in labels)
    assert all("retry_required" not in label for label in labels)
    assert all("not_ready" not in label for label in labels)
