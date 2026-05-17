from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.desktop.activation import (
    ActivationOutcome,
    FakeActivationService,
    request_manual_activation,
)
from gaze.dev.fakes import FakeFrontmostApp


def ready_state_with_target(app_name: str = "Terminal") -> GazeAppState:
    return GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(TargetSummary(app_name=app_name, confidence=0.9, locked=True))


def test_activation_module_contains_no_synthetic_click_path() -> None:
    source = __import__("pathlib").Path("src/gaze/desktop/activation.py").read_text()

    forbidden = ("CGEvent", "AXPress", "postEvent", "mouseDown", "mouseUp", "CGWarp")

    assert all(token not in source for token in forbidden)


def test_disabled_state_blocks_activation() -> None:
    service = FakeActivationService()

    outcome = request_manual_activation(GazeAppState.default(), service)

    assert outcome == ActivationOutcome.DISABLED
    assert service.calls == []


def test_no_locked_target_blocks_activation() -> None:
    service = FakeActivationService()
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    )

    outcome = request_manual_activation(state, service)

    assert outcome == ActivationOutcome.NO_TARGET
    assert service.calls == []


def test_already_frontmost_suppresses_activation() -> None:
    frontmost = FakeFrontmostApp()
    frontmost.set_frontmost("Terminal")
    service = FakeActivationService(frontmost=frontmost)

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.ALREADY_FRONTMOST
    assert service.calls == []


def test_locked_non_frontmost_target_activates_once() -> None:
    service = FakeActivationService()

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.SUCCESS
    assert service.calls == ["Terminal"]


def test_activation_failure_returns_unavailable() -> None:
    service = FakeActivationService(should_succeed=False)

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.UNAVAILABLE
