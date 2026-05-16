"""Callable command seams for hotkeys and menu actions."""

from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome


class GazeCommandController:
    def __init__(self, prototype: FakePrototypeController) -> None:
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
