from __future__ import annotations

from dataclasses import dataclass

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.feedback import FeedbackEvent, FeedbackKind, feedback_for_activation
from gaze.core.real_trust_preview import RealTrustPreviewController
from gaze.core.state import GazeFeatureFlags
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import BorderOverlayStyle, appkit_overlay_window_config
from gaze.overlays.heatmap import HeatmapPoint, RecordingHeatmapOverlay
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
    def start(self) -> CalibrationResult:
        return CalibrationResult.ready(display_layout=_layout())


class RecordingSampleSource:
    def __init__(self, sample: Sample | None) -> None:
        self.sample = sample

    def current_sample(self) -> Sample | None:
        return self.sample


class RecordingWindowProvider:
    def current_candidates(self) -> tuple[WindowCandidateSummary, ...]:
        return (
            WindowCandidateSummary(
                app_name="Terminal",
                bounds_x=0,
                bounds_y=0,
                bounds_width=500,
                bounds_height=500,
                confidence=1.0,
                owner_process_id=4242,
            ),
        )


class RecordingDisplayProvider:
    def current_layout(self) -> DisplayLayoutSnapshot:
        return _layout()


class RecordingFeedbackSurface:
    def __init__(self) -> None:
        self.events: list[FeedbackEvent] = []

    def show(self, event: FeedbackEvent) -> None:
        self.events.append(event)


class RecordingBorderOverlay:
    def __init__(self) -> None:
        self.visible = False

    def show(self, candidate: WindowCandidateSummary) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False


def _layout() -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=1,
                x=0,
                y=0,
                width=1440,
                height=900,
                scale=2.0,
                built_in=True,
            ),
        )
    )


def test_border_style_uses_soft_glow_and_thin_outline_scalars() -> None:
    style = BorderOverlayStyle.default()

    assert style.line_width <= 1.5
    assert style.glow_radius >= 14.0
    assert 0.10 <= style.glow_opacity <= 0.30
    assert 0.45 <= style.outline_opacity <= 0.90

    config = appkit_overlay_window_config(style)
    assert config["draws_thin_outline"] is True
    assert config["draws_soft_glow"] is True
    assert config["line_width"] == style.line_width
    assert config["glow_radius"] == style.glow_radius
    assert config["glow_opacity"] == style.glow_opacity
    assert config["outline_opacity"] == style.outline_opacity


def test_heatmap_is_optional_off_by_default_session_local_and_clearable() -> None:
    assert GazeFeatureFlags().heatmap_enabled is False
    overlay = RecordingHeatmapOverlay(max_points=2)

    overlay.show()
    overlay.add_point(HeatmapPoint(x=10.0, y=20.0, confidence=0.75))
    overlay.add_point(HeatmapPoint(x=11.0, y=21.0, confidence=0.80))
    overlay.add_point(HeatmapPoint(x=12.0, y=22.0, confidence=0.85))

    assert overlay.visible is True
    assert overlay.points == (
        HeatmapPoint(x=11.0, y=21.0, confidence=0.80),
        HeatmapPoint(x=12.0, y=22.0, confidence=0.85),
    )
    assert "Terminal" not in repr(overlay.points)

    overlay.clear()
    assert overlay.points == ()
    assert overlay.visible is True

    overlay.hide()
    assert overlay.visible is False


def test_feedback_events_are_subtle_non_modal_and_do_not_intercept_input() -> None:
    success = feedback_for_activation(ActivationOutcome.SUCCESS)
    failure = feedback_for_activation(ActivationOutcome.UNAVAILABLE)
    no_target = feedback_for_activation(ActivationOutcome.NO_TARGET)

    assert success.kind == FeedbackKind.SUCCESS
    assert failure.kind == FeedbackKind.FAILURE
    assert no_target.kind == FeedbackKind.NEUTRAL
    assert success.non_modal is True
    assert success.intercepts_input is False
    assert success.ttl_ms <= 1400
    assert failure.ttl_ms <= 1800
    assert success.message == "Activation sent"
    assert "Terminal" not in repr(success)


def test_real_preview_heatmap_is_opt_in_session_local_and_clearable() -> None:
    heatmap = RecordingHeatmapOverlay()
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=RecordingCalibrationSession(),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=120, confidence=0.9)),
        window_provider=RecordingWindowProvider(),
        display_provider=RecordingDisplayProvider(),
        heatmap=heatmap,
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)
    assert heatmap.visible is False
    assert heatmap.points == ()

    controller.toggle_heatmap_enabled()
    controller.tick(now_seconds=1.0, now_ms=800)
    assert heatmap.visible is True
    assert heatmap.points == (HeatmapPoint(x=100, y=120, confidence=0.9),)

    controller.clear_heatmap_session()
    assert heatmap.visible is True
    assert heatmap.points == ()

    controller.toggle_heatmap_enabled()
    assert heatmap.visible is False


def test_real_preview_without_heatmap_overlay_reports_unavailable_instead_of_silent_noop() -> None:
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=RecordingCalibrationSession(),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=120, confidence=0.9)),
        window_provider=RecordingWindowProvider(),
        display_provider=RecordingDisplayProvider(),
    )

    controller.toggle_heatmap_enabled()

    assert controller.state.flags.heatmap_enabled is False
    assert controller.state.last_status_message == "Heatmap unavailable"


def test_real_preview_activation_feedback_is_non_modal_and_content_safe() -> None:
    feedback = RecordingFeedbackSurface()
    controller = RealTrustPreviewController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=RecordingCalibrationSession(),
        sample_source=RecordingSampleSource(Sample(timestamp=1.0, x=100, y=120, confidence=0.9)),
        window_provider=RecordingWindowProvider(),
        display_provider=RecordingDisplayProvider(),
        feedback=feedback,
    )

    controller.enable_gaze()
    controller.start_calibration()
    controller.tick(now_seconds=1.0, now_ms=400)
    controller.tick(now_seconds=1.0, now_ms=800)
    controller.tick(now_seconds=1.0, now_ms=1200)
    controller.activate()

    assert len(feedback.events) == 1
    event = feedback.events[0]
    assert event.non_modal is True
    assert event.intercepts_input is False
    assert event.message in {"Activation sent", "Already focused"}
    assert "Terminal" not in repr(event)
