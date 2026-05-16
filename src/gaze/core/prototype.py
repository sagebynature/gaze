"""Pure fake prototype controller for the first Gaze trust loop."""

from __future__ import annotations

from dataclasses import replace

from gaze.core.state import CalibrationStatus, GazeAppState, GazeReadiness
from gaze.core.target_lock import TargetLockPolicy, TargetObservation
from gaze.desktop.activation import (
    ActivationOutcome,
    FakeActivationService,
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
        self._lock_override: bool | None = None
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

    def start_scripted_demo(self) -> None:
        self._targets = FakeTargetController.scripted_demo()
        self.enable_gaze()
        self.state = replace(self.state, last_status_message="Scripted demo running")

    def stop_scripted_demo(self) -> None:
        self._targets.clear_target()
        self._lock = TargetLockPolicy(stability_ms=400)
        self._lock_override = None
        self.state = self.state.with_target(None)
        self._overlay.hide()
        self.state = replace(self.state, last_status_message="Scripted demo stopped")

    def advance_scripted_demo(self, *, now_ms: int) -> None:
        self._targets.advance_script()
        self.tick(now_ms=now_ms)
        self.state = replace(self.state, last_status_message="Scripted demo running")

    def set_fake_target(self, target: FakeTarget) -> None:
        self._targets.set_manual_target(target)

    def clear_fake_target(self) -> None:
        self._targets.clear_target()
        self.state = self.state.with_target(None)
        self._overlay.hide()

    def set_fake_target_bounds(self, *, x: int, y: int, width: int, height: int) -> None:
        self._targets.update_current_bounds(x=x, y=y, width=width, height=height)
        self._refresh_current_target_from_fake()

    def set_fake_confidence(self, confidence: float) -> None:
        self._targets.update_current_confidence(confidence)
        self._refresh_current_target_from_fake()

    def override_fake_lock_state(self, locked: bool) -> None:
        self._lock_override = locked
        target = self._targets.current_fake_target()
        target_summary = None if target is None else target.as_target_summary(locked=locked)
        self.state = self.state.with_target(target_summary)
        self._sync_overlay_to_current_fake_target()

    def set_fake_frontmost_app(self, app_name: str | None) -> None:
        if isinstance(self._activation, FakeActivationService):
            self._activation.set_frontmost_app(app_name)

    def set_activation_success(self, success: bool) -> None:
        if isinstance(self._activation, FakeActivationService):
            self._activation.set_should_succeed(success)

    def mark_calibration_degraded(self) -> None:
        self.state = replace(
            self.state,
            readiness=replace(self.state.readiness, calibration=CalibrationStatus.DEGRADED),
            last_status_message="Calibration degraded",
        )

    def toggle_border_enabled(self) -> None:
        enabled = not self.state.flags.target_border_enabled
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, target_border_enabled=enabled),
            overlay_visible=self.state.overlay_visible and enabled,
        )
        if enabled:
            self._sync_overlay_to_current_fake_target()
        else:
            self._overlay.hide()

    def toggle_heatmap_enabled(self) -> None:
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, heatmap_enabled=not self.state.flags.heatmap_enabled),
        )

    def start_fake_recalibration(self) -> None:
        self.state = replace(
            self.state.with_target(None),
            readiness=replace(self.state.readiness, calibration=CalibrationStatus.CALIBRATING),
            last_status_message="Calibrating",
        )
        self._overlay.hide()

    def developer_actions(self):
        from gaze.ui.developer_actions import DeveloperPanelActions

        return DeveloperPanelActions(self)

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
        locked = self._lock_override if self._lock_override is not None else lock.locked
        if fake_target is None or not locked:
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

    def _refresh_current_target_from_fake(self) -> None:
        target = self._targets.current_fake_target()
        if target is None:
            self.state = self.state.with_target(None)
            return
        locked = False
        if self.state.current_target is not None:
            locked = self.state.current_target.locked
        if self._lock_override is not None:
            locked = self._lock_override
        self.state = self.state.with_target(target.as_target_summary(locked=locked))
        self._sync_overlay_to_current_fake_target()

    def _sync_overlay_to_current_fake_target(self) -> None:
        target = self._targets.current_fake_target()
        if (
            target is not None
            and self.state.flags.gaze_enabled
            and self.state.flags.target_border_enabled
            and self.state.current_target is not None
            and self.state.current_target.locked
        ):
            self._overlay.show(target.as_window_candidate())
        else:
            self._overlay.hide()
