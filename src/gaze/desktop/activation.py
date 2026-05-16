"""Window activation protocol boundary.

Real activation must use AppKit application activation, not synthetic clicks.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any, Protocol, cast

from gaze.core.state import GazeAppState, TargetSummary
from gaze.dev.fakes import FakeFrontmostApp


class ActivationOutcome(StrEnum):
    DISABLED = "disabled"
    NO_TARGET = "no_target"
    ALREADY_FRONTMOST = "already_frontmost"
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


class RunningApplication(Protocol):
    """Small PyObjC-compatible surface used for activation."""

    def processIdentifier(self) -> int:
        """Return the owning process id."""
        ...

    def isActive(self) -> bool:
        """Return whether this running app is already active."""
        ...

    def activateWithOptions_(self, options: int) -> bool:
        """Ask macOS to activate the app and return whether it accepted."""
        ...


class RunningApplicationWorkspace(Protocol):
    """Small NSWorkspace-compatible frontmost-app surface."""

    def frontmostApplication(self) -> RunningApplication | None:
        """Return the current frontmost app if available."""
        ...


class TargetActivationService(Protocol):
    def activate_target(self, target: TargetSummary) -> ActivationOutcome:
        """Activate the target owning app or return unavailable."""
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

    def activate_target(self, target: TargetSummary) -> ActivationOutcome:
        return self.activate_app(target.app_name)

    def activate_app(self, app_name: str) -> ActivationOutcome:
        if self._frontmost.is_frontmost(app_name):
            return ActivationOutcome.ALREADY_FRONTMOST
        if not self._should_succeed:
            return ActivationOutcome.UNAVAILABLE
        self.calls.append(app_name)
        self._frontmost.set_frontmost(app_name)
        return ActivationOutcome.SUCCESS

    def set_frontmost_app(self, app_name: str | None) -> None:
        self._frontmost.set_frontmost(app_name)

    def set_should_succeed(self, should_succeed: bool) -> None:
        self._should_succeed = should_succeed


class AppKitActivationService:
    """Activate a locked target by owning process identity using AppKit."""

    def __init__(
        self,
        *,
        workspace_factory: Callable[[], RunningApplicationWorkspace] | None = None,
        running_app_lookup: Callable[[int], RunningApplication | None] | None = None,
        activation_options: int | None = None,
    ) -> None:
        self._workspace_factory = workspace_factory
        self._running_app_lookup = running_app_lookup
        self._activation_options = activation_options

    def activate_target(self, target: TargetSummary) -> ActivationOutcome:
        process_id = target.owner_process_id
        if process_id is None:
            return ActivationOutcome.UNAVAILABLE

        frontmost = self._workspace().frontmostApplication()
        if frontmost is not None and _process_id(frontmost) == process_id:
            return ActivationOutcome.ALREADY_FRONTMOST

        app = self._running_app(process_id)
        if app is None:
            return ActivationOutcome.UNAVAILABLE
        if app.isActive():
            return ActivationOutcome.ALREADY_FRONTMOST
        if app.activateWithOptions_(self._options()):
            return ActivationOutcome.SUCCESS
        return ActivationOutcome.UNAVAILABLE

    def _workspace(self) -> RunningApplicationWorkspace:
        if self._workspace_factory is not None:
            return self._workspace_factory()
        appkit = cast(Any, __import__("AppKit"))
        return cast(RunningApplicationWorkspace, appkit.NSWorkspace.sharedWorkspace())

    def _running_app(self, process_id: int) -> RunningApplication | None:
        if self._running_app_lookup is not None:
            return self._running_app_lookup(process_id)
        appkit = cast(Any, __import__("AppKit"))
        apps = appkit.NSRunningApplication.runningApplicationsWithProcessIdentifier_(process_id)
        return cast(RunningApplication, apps[0]) if apps else None

    def _options(self) -> int:
        if self._activation_options is not None:
            return self._activation_options
        appkit = cast(Any, __import__("AppKit"))
        return int(appkit.NSApplicationActivateIgnoringOtherApps)


def request_manual_activation(
    state: GazeAppState,
    service: TargetActivationService,
) -> ActivationOutcome:
    if not state.flags.gaze_enabled:
        return ActivationOutcome.DISABLED
    if state.activation_blocked or state.current_target is None:
        return ActivationOutcome.NO_TARGET
    return service.activate_target(state.current_target)


def _process_id(app: RunningApplication) -> int:
    return app.processIdentifier()
