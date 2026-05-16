"""Callable command seams for hotkeys and menu actions."""

from __future__ import annotations

from typing import Protocol

from gaze.core.state import GazeAppState
from gaze.desktop.activation import ActivationOutcome


class GazeCommandTarget(Protocol):
    """Controller surface used by menu items and hotkeys."""

    state: GazeAppState

    def activate(self) -> ActivationOutcome:
        """Request manual target activation."""
        ...

    def enable_gaze(self) -> None:
        """Enable gaze tracking/preview."""
        ...

    def disable_gaze(self) -> None:
        """Disable gaze tracking/preview."""
        ...

    def start_calibration(self) -> None:
        """Start user-initiated calibration."""
        ...


class GazeCommandController:
    def __init__(self, prototype: GazeCommandTarget) -> None:
        self._prototype = prototype

    def manual_activate_command(self) -> ActivationOutcome:
        return self._prototype.activate()

    def toggle_gaze_command(self) -> None:
        if self._prototype.state.flags.gaze_enabled:
            self._prototype.disable_gaze()
        else:
            self._prototype.enable_gaze()

    def recalibrate_command(self) -> None:
        self._prototype.start_calibration()
