"""Window activation protocol boundary.

Real activation must use AppKit application activation, not synthetic clicks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from gaze.core.state import GazeAppState
from gaze.dev.fakes import FakeFrontmostApp


class ActivationOutcome(StrEnum):
    DISABLED = "disabled"
    NO_TARGET = "no_target"
    ALREADY_FRONTMOST = "already_frontmost"
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


class TargetActivationService(Protocol):
    def activate_app(self, app_name: str) -> ActivationOutcome:
        """Activate the owning app by app name or return unavailable."""
        ...


class FakeActivationService:
    def __init__(
        self,
        *,
        frontmost: FakeFrontmostApp | None = None,
        should_succeed: bool = True,
    ) -> None:
        self._frontmost = frontmost or FakeFrontmostApp()
        self._should_succeed = should_succeed
        self.calls: list[str] = []

    def activate_app(self, app_name: str) -> ActivationOutcome:
        if self._frontmost.is_frontmost(app_name):
            return ActivationOutcome.ALREADY_FRONTMOST
        if not self._should_succeed:
            return ActivationOutcome.UNAVAILABLE
        self.calls.append(app_name)
        self._frontmost.set_frontmost(app_name)
        return ActivationOutcome.SUCCESS


def request_manual_activation(
    state: GazeAppState,
    service: TargetActivationService,
) -> ActivationOutcome:
    if not state.flags.gaze_enabled:
        return ActivationOutcome.DISABLED
    if state.activation_blocked or state.current_target is None:
        return ActivationOutcome.NO_TARGET
    return service.activate_app(state.current_target.app_name)
