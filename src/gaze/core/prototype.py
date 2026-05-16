"""Pure fake prototype controller for the first Gaze trust loop."""

from __future__ import annotations

from dataclasses import replace

from gaze.core.state import CalibrationStatus, GazeAppState, GazeReadiness
from gaze.core.target_lock import TargetLockPolicy, TargetObservation
from gaze.desktop.activation import (
    ActivationOutcome,
    TargetActivationService,
    request_manual_activation,
)
from gaze.dev.fakes import FakeTarget, FakeTargetController
from gaze.overlays.border import TargetBorderOverlay


class FakePrototypeController:
    def __init__(
        self,
        *,
        overlay: TargetBorderOverlay,
        activation: TargetActivationService,
        target_controller: FakeTargetController | None = None,
    ) -> None:
        self._overlay = overlay
        self._activation = activation
        self._targets = target_controller or FakeTargetController()
        self._lock = TargetLockPolicy(stability_ms=400)
        self.state = GazeAppState.default()

    def enable_gaze(self) -> None:
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, gaze_enabled=True),
            readiness=GazeReadiness(
                calibration=CalibrationStatus.READY,
                camera_available=True,
                tracker_available=True,
            ),
            last_status_message="Gaze ready",
        )

    def disable_gaze(self) -> None:
        self.state = self.state.disable_panic()
        self._overlay.hide()

    def set_fake_target(self, target: FakeTarget) -> None:
        self._targets.set_manual_target(target)

    def clear_fake_target(self) -> None:
        self._targets.clear_target()

    def tick(self, *, now_ms: int) -> None:
        if not self.state.flags.gaze_enabled:
            self.state = self.state.with_target(None)
            self._overlay.hide()
            return

        fake_target = self._targets.current_fake_target()
        observation = None
        if fake_target is not None:
            observation = TargetObservation(fake_target.app_name, fake_target.confidence)
        lock = self._lock.update(observation, now_ms=now_ms)
        if fake_target is None or not lock.locked:
            self.state = self.state.with_target(None)
            self._overlay.hide()
            return

        target_summary = fake_target.as_target_summary(locked=True)
        self.state = self.state.with_target(target_summary)
        self._overlay.show(fake_target.as_window_candidate())

    def activate(self) -> ActivationOutcome:
        outcome = request_manual_activation(self.state, self._activation)
        target_name = self.state.current_target.app_name if self.state.current_target else "target"
        message = {
            ActivationOutcome.DISABLED: "Gaze disabled",
            ActivationOutcome.NO_TARGET: "No target",
            ActivationOutcome.ALREADY_FRONTMOST: "Already frontmost",
            ActivationOutcome.SUCCESS: f"Activated {target_name}",
            ActivationOutcome.UNAVAILABLE: "Activation unavailable",
        }[outcome]
        self.state = replace(self.state, last_status_message=message)
        return outcome
