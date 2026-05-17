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

    assert "Status: ready" in labels
    assert "Target: Terminal" in labels
    assert "Calibration: ready" in labels
    assert "Lock: locked" in labels
    assert "Cmd+G: activate locked target" in labels
    assert "Auto-activate: off" in labels
    assert "Disable Gaze" in labels
    assert "Toggle Border" in labels
    assert "Recalibrate" in labels
    assert "Toggle Heatmap" not in labels
    assert all(not label.startswith("Confidence:") for label in labels)
    assert "Settings" in labels
    assert "Quit" in labels
    assert all(" - " not in label for label in labels)
