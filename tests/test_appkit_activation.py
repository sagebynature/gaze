import importlib
import sys

from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.desktop.activation import (
    ActivationOutcome,
    AppKitActivationService,
    request_manual_activation,
)


class FakeRunningApplication:
    def __init__(
        self,
        *,
        process_id: int,
        active: bool = False,
        activation_result: bool = True,
    ) -> None:
        self._process_id = process_id
        self._active = active
        self._activation_result = activation_result
        self.activation_options: list[int] = []

    def processIdentifier(self) -> int:
        return self._process_id

    def isActive(self) -> bool:
        return self._active

    def activateWithOptions_(self, options: int) -> bool:
        self.activation_options.append(options)
        self._active = self._activation_result
        return self._activation_result


class FakeWorkspace:
    def __init__(self, frontmost: FakeRunningApplication | None = None) -> None:
        self._frontmost = frontmost

    def frontmostApplication(self) -> FakeRunningApplication | None:
        return self._frontmost


def ready_state_with_target(
    *,
    owner_process_id: int | None,
    app_name: str = "Terminal",
) -> GazeAppState:
    return GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(
        TargetSummary(
            app_name=app_name,
            confidence=0.9,
            locked=True,
            owner_process_id=owner_process_id,
        )
    )


def test_appkit_activation_import_does_not_load_appkit() -> None:
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.desktop.activation")

    assert "AppKit" not in sys.modules


def test_missing_process_identity_returns_unavailable_without_activation() -> None:
    service = AppKitActivationService(
        workspace_factory=lambda: FakeWorkspace(),
        running_app_lookup=lambda process_id: None,
        activation_options=64,
    )

    outcome = request_manual_activation(
        ready_state_with_target(owner_process_id=None),
        service,
    )

    assert outcome == ActivationOutcome.UNAVAILABLE


def test_already_frontmost_process_returns_already_frontmost_without_activation() -> None:
    app = FakeRunningApplication(process_id=777, active=True)
    service = AppKitActivationService(
        workspace_factory=lambda: FakeWorkspace(frontmost=app),
        running_app_lookup=lambda process_id: app,
        activation_options=64,
    )

    outcome = request_manual_activation(
        ready_state_with_target(owner_process_id=777),
        service,
    )

    assert outcome == ActivationOutcome.ALREADY_FRONTMOST
    assert app.activation_options == []


def test_non_frontmost_process_activates_by_process_identity() -> None:
    app = FakeRunningApplication(process_id=777, active=False, activation_result=True)
    service = AppKitActivationService(
        workspace_factory=lambda: FakeWorkspace(),
        running_app_lookup=lambda process_id: app if process_id == 777 else None,
        activation_options=64,
    )

    outcome = request_manual_activation(
        ready_state_with_target(owner_process_id=777),
        service,
    )

    assert outcome == ActivationOutcome.SUCCESS
    assert app.activation_options == [64]


def test_macos_activation_refusal_returns_unavailable() -> None:
    app = FakeRunningApplication(process_id=777, active=False, activation_result=False)
    service = AppKitActivationService(
        workspace_factory=lambda: FakeWorkspace(),
        running_app_lookup=lambda process_id: app,
        activation_options=64,
    )

    outcome = request_manual_activation(
        ready_state_with_target(owner_process_id=777),
        service,
    )

    assert outcome == ActivationOutcome.UNAVAILABLE
    assert app.activation_options == [64]
