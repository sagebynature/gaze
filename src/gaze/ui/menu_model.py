"""Pure menu model for the menu-bar dropdown."""

from __future__ import annotations

from dataclasses import dataclass

from gaze.core.state import GazeAppState


@dataclass(frozen=True)
class MenuItem:
    label: str
    action: str | None = None


def menu_items_for_state(state: GazeAppState) -> list[MenuItem]:
    target_label = "No target"
    confidence_label = "Confidence: --"
    lock_label = "Lock: unlocked"
    if state.current_target is not None:
        target_label = state.current_target.app_name
        confidence_label = f"Confidence: {state.current_target.confidence:.2f}"
        lock_label = "Lock: locked" if state.current_target.locked else "Lock: unlocked"

    return [
        MenuItem(f"Status: {state.menu_status}"),
        MenuItem(f"Calibration: {state.readiness.calibration.value}"),
        MenuItem(f"Target: {target_label}"),
        MenuItem(confidence_label),
        MenuItem(lock_label),
        MenuItem("Disable Gaze" if state.flags.gaze_enabled else "Enable Gaze", "toggle_gaze"),
        MenuItem("Toggle Border", "toggle_border"),
        MenuItem("Toggle Heatmap", "toggle_heatmap"),
        MenuItem("Recalibrate", "recalibrate"),
        MenuItem("Settings", "settings"),
        MenuItem("Quit", "quit"),
    ]
