from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus
from gaze.desktop.activation import ActivationOutcome
from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import RecordingBorderOverlay
from gaze.tracking.calibration import CalibrationResult
from gaze.tracking.gaze_pipeline import PupilTrackerGazeSample


@dataclass(frozen=True)
class Sample(PupilTrackerGazeSample):
    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool = True


class RecordingCalibrationSession:
    def __init__(
        self,
        result: CalibrationResult,
        *,
        ignored_owner_process_ids: frozenset[int] = frozenset(),
    ) -> None:
        self.result = result
        self.starts = 0
        self._ignored_owner_process_ids = ignored_owner_process_ids

    def start(self) -> CalibrationResult:
        self.starts += 1
        return self.result

    def ignored_owner_process_ids(self) -> frozenset[int]:
        return self._ignored_owner_process_ids


class RecordingSampleSource:
    def __init__(self, *samples: Sample | None) -> None:
        self.samples = list(samples)
        self.calls = 0

    def current_sample(self) -> Sample | None:
        self.calls += 1
        if not self.samples:
            return None
        return self.samples.pop(0)


class RecordingWindowProvider:
    def __init__(self, candidates: tuple[WindowCandidateSummary, ...]) -> None:
        self.candidates = candidates
        self.calls = 0

    def current_candidates(self) -> tuple[WindowCandidateSummary, ...]:
        self.calls += 1
        return self.candidates


class RecordingDisplayProvider:
    def __init__(self, layout: DisplayLayoutSnapshot) -> None:
        self.layout = layout
        self.calls = 0

    def current_layout(self) -> DisplayLayoutSnapshot:
        self.calls += 1
        return self.layout


class RecordingActivationService:
    def __init__(self, outcome: ActivationOutcome = ActivationOutcome.SUCCESS) -> None:
        self.outcome = outcome
        self.targets: list[str] = []

    def activate_target(self, target: Any) -> ActivationOutcome:
        self.targets.append(f"{target.app_name}:{target.owner_process_id}")
        return self.outcome


def layout(display_id: int = 1, *, x: float = 0, width: float = 1440) -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=display_id,
                x=x,
                y=0,
                width=width,
                height=900,
                scale=2.0,
                built_in=True,
            ),
        )
    )


def candidate(
    app_name: str = "Terminal",
    *,
    owner_process_id: int | None = 4242,
    bounds_x: float = 0,
    bounds_y: float = 0,
    bounds_width: float = 500,
    bounds_height: float = 500,
) -> WindowCandidateSummary:
    return WindowCandidateSummary(
        app_name=app_name,
        bounds_x=bounds_x,
        bounds_y=bounds_y,
        bounds_width=bounds_width,
        bounds_height=bounds_height,
        confidence=1.0,
        owner_process_id=owner_process_id,
    )


def test_real_trust_preview_import_is_safe() -> None:
    sys.modules.pop("AppKit", None)
    sys.modules.pop("Quartz", None)
    import gaze.core.real_trust_preview  # noqa: F401

    assert "AppKit" not in sys.modules
    assert "Quartz" not in sys.modules


def test_calibration_is_started_only_by_explicit_recalibration() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    session = RecordingCalibrationSession(CalibrationResult.ready(display_layout=display_layout))
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=RecordingActivationService(),
        calibration_session=session,
        sample_source=RecordingSampleSource(),
        window_provider=RecordingWindowProvider(()),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    assert session.starts == 0

    controller.enable_gaze()

    assert session.starts == 0
    assert controller.state.flags.gaze_enabled is True
    assert controller.state.readiness.calibration is CalibrationStatus.NOT_READY
    assert controller.state.last_status_message == "Calibration required"

    controller.start_calibration()

    assert session.starts == 1
    assert controller.state.readiness.calibration is CalibrationStatus.READY
    assert controller.state.calibration_display_layout == display_layout


def test_first_bridged_sample_after_launched_calibration_marks_ready() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult(
                status=CalibrationStatus.CALIBRATING,
                message="PupilTracker calibration launched",
                camera_available=True,
                tracker_available=True,
                display_layout=display_layout,
            )
        ),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9)),
        window_provider=RecordingWindowProvider((candidate(),)),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)

    assert controller.state.readiness.calibration is CalibrationStatus.READY
    assert controller.state.calibration_display_layout == display_layout
    assert controller.state.current_gaze_sample is not None
    assert controller.state.current_gaze_sample.valid is True


def test_fresh_bridged_sample_after_enable_marks_ready_without_relaunching_calibration() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    session = RecordingCalibrationSession(CalibrationResult.ready(display_layout=display_layout))
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=RecordingActivationService(),
        calibration_session=session,
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9)),
        window_provider=RecordingWindowProvider((candidate(),)),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    controller.enable_gaze()
    controller.tick(now_seconds=1.0, now_ms=400)

    assert session.starts == 0
    assert controller.state.readiness.calibration is CalibrationStatus.READY
    assert controller.state.readiness.camera_available is True
    assert controller.state.readiness.tracker_available is True
    assert controller.state.calibration_display_layout == display_layout
    assert controller.state.current_gaze_sample is not None
    assert controller.state.current_gaze_sample.valid is True


def test_tick_locks_real_window_target_and_shows_border_after_stability() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    overlay = RecordingBorderOverlay()
    controller = RealTrustPreviewController(
        overlay=overlay,
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.ready(display_layout=display_layout)
        ),
        sample_source=RecordingSampleSource(
            Sample(timestamp=1.0, x=100, y=100, confidence=0.9),
            Sample(timestamp=1.1, x=110, y=100, confidence=0.9),
        ),
        window_provider=RecordingWindowProvider((candidate(),)),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=0)

    assert controller.state.current_target is None
    assert overlay.visible is False

    controller.tick(now_seconds=1.1, now_ms=400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.app_name == "Terminal"
    assert controller.state.current_target.owner_process_id == 4242
    assert overlay.visible is True
    assert overlay.last_candidate == candidate()


def test_tick_ignores_launched_pupil_tracker_demo_process_as_target() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    overlay = RecordingBorderOverlay()
    controller = RealTrustPreviewController(
        overlay=overlay,
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.ready(display_layout=display_layout),
            ignored_owner_process_ids=frozenset({31337}),
        ),
        sample_source=RecordingSampleSource(
            Sample(timestamp=1.0, x=100, y=100, confidence=0.9),
            Sample(timestamp=1.1, x=110, y=100, confidence=0.9),
        ),
        window_provider=RecordingWindowProvider(
            (
                candidate("PupilTracker Demo", owner_process_id=31337),
                candidate("Code", owner_process_id=4242),
            )
        ),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=0)
    controller.tick(now_seconds=1.1, now_ms=400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.app_name == "Code"
    assert controller.state.current_target.owner_process_id == 4242
    assert overlay.visible is True
    assert overlay.last_candidate == candidate("Code", owner_process_id=4242)


def test_manual_activation_uses_locked_real_target_process_identity() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    display_layout = layout()
    activation = RecordingActivationService()
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=activation,
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.ready(display_layout=display_layout)
        ),
        sample_source=RecordingSampleSource(
            Sample(timestamp=1.0, x=100, y=100, confidence=0.9),
            Sample(timestamp=1.1, x=110, y=100, confidence=0.9),
        ),
        window_provider=RecordingWindowProvider((candidate("Code"),)),
        display_provider=RecordingDisplayProvider(display_layout),
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=0)
    controller.tick(now_seconds=1.1, now_ms=400)

    assert controller.activate() is ActivationOutcome.SUCCESS
    assert activation.targets == ["Code:4242"]
    assert controller.state.last_status_message == "Activated Code"


def test_display_layout_change_degrades_and_hides_border_without_raw_content() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    calibrated_layout = layout(display_id=1)
    changed_layout = layout(display_id=2, x=1440, width=1920)
    overlay = RecordingBorderOverlay()
    controller = RealTrustPreviewController(
        overlay=overlay,
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.ready(display_layout=calibrated_layout)
        ),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9)),
        window_provider=RecordingWindowProvider((candidate(),)),
        display_provider=RecordingDisplayProvider(changed_layout),
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)

    assert controller.state.readiness.calibration is CalibrationStatus.DEGRADED
    assert controller.state.current_target is None
    assert overlay.visible is False
    assert "Display layout changed" in controller.state.last_status_message
    assert " - " not in controller.state.last_status_message


def test_disabled_tick_preserves_recalibration_failure_guidance() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(
            CalibrationResult.unavailable("Calibration UI unavailable in this bundle")
        ),
        sample_source=RecordingSampleSource(),
        window_provider=RecordingWindowProvider(()),
        display_provider=RecordingDisplayProvider(layout()),
    )

    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)

    assert controller.state.readiness.calibration is CalibrationStatus.RETRY_REQUIRED
    assert controller.state.last_status_message == "Calibration UI unavailable in this bundle"


def test_tick_while_disabled_does_not_touch_camera_windows_or_displays() -> None:
    from gaze.core.real_trust_preview import RealTrustPreviewController

    sample_source = RecordingSampleSource(Sample(timestamp=1.0, x=100, y=100, confidence=0.9))
    window_provider = RecordingWindowProvider((candidate(),))
    display_provider = RecordingDisplayProvider(layout())
    overlay = RecordingBorderOverlay()
    controller = RealTrustPreviewController(
        overlay=overlay,
        activation=RecordingActivationService(),
        calibration_session=RecordingCalibrationSession(CalibrationResult.ready()),
        sample_source=sample_source,
        window_provider=window_provider,
        display_provider=display_provider,
    )

    controller.tick(now_seconds=1.0, now_ms=400)

    assert sample_source.calls == 0
    assert window_provider.calls == 0
    assert display_provider.calls == 0
    assert overlay.visible is False
