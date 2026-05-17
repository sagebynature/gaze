from __future__ import annotations

from dataclasses import dataclass

import pytest

from gaze.core.diagnostics import (
    DiagnosticsProfile,
    ScalarDiagnostics,
    default_diagnostics_profile,
)
from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.prototype import FakePrototypeController
from gaze.core.real_trust_preview import RealTrustPreviewController
from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    GazeSampleSummary,
    TargetSummary,
)
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import RecordingBorderOverlay
from gaze.tracking.calibration import CalibrationResult
from gaze.tracking.gaze_pipeline import PupilTrackerGazeSample
from gaze.ui.appkit_shell import build_menu_bar_app
from test_appkit_shell_model import FakeAppKit


@dataclass(frozen=True)
class UnsafeFrame:
    pixels: bytes


@dataclass(frozen=True)
class Sample(PupilTrackerGazeSample):
    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool = True


class RecordingCalibrationSession:
    def __init__(self, result: CalibrationResult) -> None:
        self.result = result

    def start(self) -> CalibrationResult:
        return self.result


class RecordingSampleSource:
    def __init__(self, sample: Sample | None = None) -> None:
        self.sample = sample

    def current_sample(self) -> Sample | None:
        return self.sample


class RecordingWindowProvider:
    def __init__(self, candidates: tuple[WindowCandidateSummary, ...]) -> None:
        self.candidates = candidates

    def current_candidates(self) -> tuple[WindowCandidateSummary, ...]:
        return self.candidates


class RecordingDisplayProvider:
    def __init__(self, layout: DisplayLayoutSnapshot) -> None:
        self.layout = layout

    def current_layout(self) -> DisplayLayoutSnapshot:
        return self.layout


def _layout(display_id: int = 1) -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=display_id,
                x=0,
                y=0,
                width=1440,
                height=900,
                scale=2.0,
                built_in=True,
            ),
        )
    )


def _candidate(app_name: str = "Terminal") -> WindowCandidateSummary:
    return WindowCandidateSummary(
        app_name=app_name,
        bounds_x=0,
        bounds_y=0,
        bounds_width=500,
        bounds_height=500,
        confidence=1.0,
        owner_process_id=4242,
    )


def _tracking_state() -> GazeAppState:
    return GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_gaze_sample(
        GazeSampleSummary(
            timestamp=1.0,
            x=100.0,
            y=200.0,
            confidence=0.87,
            valid=True,
        )
    )


def test_diagnostics_profile_defaults_on_for_dev_and_off_for_release() -> None:
    assert default_diagnostics_profile(development_mode=True).enabled is True
    assert default_diagnostics_profile(development_mode=False).enabled is False
    assert DiagnosticsProfile.release().enabled is False


def test_scalar_diagnostics_records_state_without_target_names_or_raw_content() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())
    state = _tracking_state().with_target(
        TargetSummary(app_name="Terminal", confidence=0.91, locked=True, owner_process_id=123)
    )

    diagnostics.record_state(state, now_ms=1000)
    diagnostics.record_state(state, now_ms=1400)

    snapshot = diagnostics.snapshot()
    assert snapshot["enabled"] is True
    assert snapshot["calibration_state"] == "ready"
    assert snapshot["last_confidence"] == 0.87
    assert snapshot["target_locked"] is True
    assert snapshot["lock_duration_ms"] == 400
    assert "Terminal" not in repr(snapshot)
    assert "app_name" not in snapshot
    assert "window_title" not in snapshot


def test_release_profile_noops_without_collecting_scalars() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.release())

    diagnostics.record_state(_tracking_state(), now_ms=1000)
    diagnostics.record_activation(ActivationOutcome.SUCCESS)

    assert diagnostics.snapshot() == {"enabled": False}


def test_activation_and_display_counters_are_scalar_only() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())

    diagnostics.record_activation(ActivationOutcome.ALREADY_FRONTMOST)
    diagnostics.record_activation(ActivationOutcome.NO_TARGET)
    diagnostics.record_activation(ActivationOutcome.NO_TARGET)
    diagnostics.record_display_layout_degraded()

    snapshot = diagnostics.snapshot()
    assert snapshot["last_activation_result"] == "no_target"
    assert snapshot["already_frontmost_count"] == 1
    assert snapshot["no_target_count"] == 2
    assert snapshot["display_layout_degraded_events"] == 1


def test_hotkey_registration_feedback_records_status_without_bindings_content() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())

    diagnostics.record_hotkey_feedback(("unavailable cmd+g for Activate Target", "conflict cmd+g"))

    snapshot = diagnostics.snapshot()
    assert snapshot["hotkey_registration_status"] == "issues"
    assert snapshot["hotkey_registration_issue_count"] == 2
    assert "cmd+g" not in repr(snapshot)
    assert "Activate Target" not in repr(snapshot)


def test_diagnostics_reject_raw_or_content_like_payloads() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())

    with pytest.raises(ValueError, match="scalar-only"):
        diagnostics.record_payload("frame", {"frame": UnsafeFrame(b"pixels")})

    with pytest.raises(ValueError, match="content"):
        diagnostics.record_payload("window", {"window_title": "Secret editor title"})


def test_menu_bar_runtime_defaults_diagnostics_on_for_dev_and_off_for_release() -> None:
    dev_runtime = build_menu_bar_app(
        appkit=FakeAppKit(),
        controller=FakePrototypeController(
            overlay=RecordingBorderOverlay(),
            activation=FakeActivationService(),
        ),
        development_mode=True,
        unavailable_hotkeys=("cmd+g",),
    )
    release_runtime = build_menu_bar_app(
        appkit=FakeAppKit(),
        controller=FakePrototypeController(
            overlay=RecordingBorderOverlay(),
            activation=FakeActivationService(),
        ),
        development_mode=False,
    )

    assert dev_runtime.diagnostics.snapshot()["enabled"] is True
    assert dev_runtime.diagnostics.snapshot()["hotkey_registration_status"] == "issues"
    assert dev_runtime.diagnostics.snapshot()["hotkey_registration_issue_count"] == 1
    assert "cmd+g" not in repr(dev_runtime.diagnostics.snapshot())
    assert release_runtime.diagnostics.snapshot() == {"enabled": False}


def test_real_preview_records_scalar_activation_and_state_counts() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())
    display_layout = _layout()
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.ready(display_layout=display_layout)
        ),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9)),
        window_provider=RecordingWindowProvider((_candidate(),)),
        display_provider=RecordingDisplayProvider(display_layout),
        diagnostics=diagnostics,
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)
    controller.tick(now_seconds=1.0, now_ms=800)
    controller.tick(now_seconds=1.0, now_ms=1200)
    controller.activate()

    snapshot = diagnostics.snapshot()
    assert snapshot["calibration_state"] == "ready"
    assert snapshot["last_confidence"] == 0.9
    assert snapshot["target_locked"] is True
    assert snapshot["lock_duration_ms"] == 400
    assert snapshot["last_activation_result"] in {"success", "already_frontmost"}
    assert "Terminal" not in repr(snapshot)


def test_real_preview_records_display_layout_degradation_as_counter_only() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=RecordingCalibrationSession(CalibrationResult.ready(display_layout=_layout(1))),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9)),
        window_provider=RecordingWindowProvider((_candidate(),)),
        display_provider=RecordingDisplayProvider(_layout(2)),
        diagnostics=diagnostics,
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)

    assert diagnostics.snapshot()["display_layout_degraded_events"] == 1
