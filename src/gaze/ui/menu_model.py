"""Pure menu model for the menu-bar dropdown."""

from __future__ import annotations

from dataclasses import dataclass

from gaze.core.state import GazeAppState
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY


@dataclass(frozen=True)
class MenuItem:
    label: str
    action: str | None = None
    key_equivalent: str = ""
    modifier_names: tuple[str, ...] = ()


def _hotkey_parts(hotkey: str) -> tuple[str, tuple[str, ...]]:
    parts = hotkey.split("+")
    return parts[-1], tuple(parts[:-1])


def _status_label(value: str) -> str:
    return value.replace("_", " ").title()


def _hotkey_label(hotkey: str) -> str:
    return "+".join(part.title() for part in hotkey.split("+"))


def menu_items_for_state(state: GazeAppState) -> list[MenuItem]:
    target_label = "No target"
    lock_label = "Lock: unlocked"
    if state.current_target is not None:
        target_label = state.current_target.app_name
        lock_label = "Lock: locked" if state.current_target.locked else "Lock: unlocked"

    manual_key, manual_modifiers = _hotkey_parts(MANUAL_ACTIVATE_HOTKEY)
    toggle_key, toggle_modifiers = _hotkey_parts(GAZE_TOGGLE_HOTKEY)
    auto_label = "Auto-activate: off"
    if state.flags.auto_activate_enabled:
        auto_label = f"Auto-activate: on after {state.flags.auto_activate_debounce_ms}ms"

    return [
        MenuItem(f"Gaze: {_status_label(state.menu_status)}"),
        MenuItem(state.last_status_message),
        MenuItem(f"Calibration: {_status_label(state.readiness.calibration.value)}"),
        MenuItem(f"Target: {target_label}"),
        MenuItem(lock_label),
        MenuItem(f"Manual activation: {_hotkey_label(MANUAL_ACTIVATE_HOTKEY)}"),
        MenuItem(
            "Target border: on" if state.flags.target_border_enabled else "Target border: off",
        ),
        MenuItem(auto_label),
        MenuItem("Activate Target", "manual_activate", manual_key, manual_modifiers),
        MenuItem(
            "Disable Gaze" if state.flags.gaze_enabled else "Enable Gaze",
            "toggle_gaze",
            toggle_key,
            toggle_modifiers,
        ),
        MenuItem("Toggle Border", "toggle_border"),
        MenuItem("Recalibrate", "recalibrate"),
        MenuItem("Settings", "settings"),
        MenuItem("Quit", "quit"),
    ]
