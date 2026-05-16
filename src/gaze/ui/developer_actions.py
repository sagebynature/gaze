"""Development-only action wiring for fake prototype controls."""

from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome
from gaze.dev.fakes import FakeTarget


class DeveloperPanelActions:
    def __init__(self, controller: FakePrototypeController) -> None:
        self._controller = controller

    def enable_gaze(self) -> None:
        self._controller.enable_gaze()

    def tick(self, *, now_ms: int) -> None:
        self._controller.tick(now_ms=now_ms)

    def start_scripted_demo(self) -> None:
        self._controller.start_scripted_demo()

    def stop_scripted_demo(self) -> None:
        self._controller.stop_scripted_demo()

    def advance_scripted_demo(self, *, now_ms: int) -> None:
        self._controller.advance_scripted_demo(now_ms=now_ms)

    def set_fake_target(
        self,
        *,
        app_name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
    ) -> None:
        self._controller.set_fake_target(FakeTarget(app_name, x, y, width, height, confidence))

    def set_fake_target_bounds(self, *, x: int, y: int, width: int, height: int) -> None:
        self._controller.set_fake_target_bounds(x=x, y=y, width=width, height=height)

    def set_fake_confidence(self, confidence: float) -> None:
        self._controller.set_fake_confidence(confidence)

    def set_fake_lock_state(self, locked: bool) -> None:
        self._controller.override_fake_lock_state(locked)

    def set_fake_frontmost_app(self, app_name: str | None) -> None:
        self._controller.set_fake_frontmost_app(app_name)

    def trigger_activation_success(self) -> None:
        self._controller.set_activation_success(True)

    def trigger_activation_failure(self) -> None:
        self._controller.set_activation_success(False)

    def trigger_no_target(self) -> None:
        self._controller.clear_fake_target()

    def trigger_degraded(self) -> None:
        self._controller.mark_calibration_degraded()

    def manual_activate(self) -> ActivationOutcome:
        return self._controller.activate()
