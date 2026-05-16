from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY
from gaze.ui.menu_model import menu_items_for_state


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
    assert "Confidence: 0.91" in labels
    assert "Lock: locked" in labels
    assert "Disable Gaze" in labels
    assert "Toggle Border" in labels
    assert "Toggle Heatmap" in labels
    assert "Recalibrate" in labels
    assert "Settings" in labels
    assert "Quit" in labels
    assert all(" - " not in label for label in labels)
