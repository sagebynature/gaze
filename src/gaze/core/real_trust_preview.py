"""Real trust-preview controller wiring calibration, gaze, windows, border, and activation.

This module is import-safe. It defines runtime seams and pure orchestration only;
it does not import AppKit, Quartz, PupilTracker, start a camera, enumerate windows,
or activate apps at import time.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any, Protocol, cast

from gaze.core.diagnostics import DiagnosticsProfile, ScalarDiagnostics
from gaze.core.display_geometry import DisplayLayoutSnapshot
from gaze.core.feedback import FeedbackEvent, feedback_for_activation
from gaze.core.state import CalibrationStatus, GazeAppState
from gaze.core.target_selection import GazeTargetSelectionPipeline, candidate_at_gaze_point
from gaze.desktop.activation import (
    ActivationOutcome,
    TargetActivationService,
    request_manual_activation,
)
from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import TargetBorderOverlay
from gaze.overlays.heatmap import HeatmapOverlay, HeatmapPoint
from gaze.tracking.calibration import (
    CalibrationOnboardingController,
    CalibrationProviderSnapshot,
    CalibrationResult,
    CalibrationSession,
)
from gaze.tracking.gaze_pipeline import GazeSamplePipeline, PupilTrackerGazeSample


class GazeSampleSource(Protocol):
    """Runtime source for one current calibrated gaze sample."""

    def current_sample(self) -> PupilTrackerGazeSample | None:
        """Return the most recent privacy-safe gaze sample, if available."""
        ...


class VisibleWindowProvider(Protocol):
    """Runtime source for visible, targetable window candidates."""

    def current_candidates(self) -> tuple[WindowCandidateSummary, ...]:
        """Return visible candidates in top-to-bottom order."""
        ...


class DisplayLayoutProvider(Protocol):
    """Runtime source for active display geometry."""

    def current_layout(self) -> DisplayLayoutSnapshot:
        """Return the active privacy-safe display layout."""
        ...


class FeedbackSurface(Protocol):
    """Shows short-lived, non-modal trust feedback."""

    def show(self, event: FeedbackEvent) -> None:
        """Show one subtle feedback event."""
        ...


class CalibrationProfileStore(Protocol):
    """Content-safe last-good calibration persistence seam."""

    def restore_for_layout(self, current_layout: DisplayLayoutSnapshot) -> CalibrationResult | None:
        """Return a restored calibration result for the current layout, if usable."""
        ...

    def save(self, result: CalibrationResult) -> None:
        """Persist a usable explicit calibration result."""
        ...


_RESTORED_CALIBRATION_MESSAGE = "Calibration restored; fresh sample required"


class RealTrustPreviewController:
    """Coordinate the real trust-preview loop without persisting visual content."""

    def __init__(
        self,
        *,
        overlay: TargetBorderOverlay,
        activation: TargetActivationService,
        calibration_session: CalibrationSession,
        sample_source: GazeSampleSource,
        window_provider: VisibleWindowProvider,
        display_provider: DisplayLayoutProvider,
        gaze_pipeline: GazeSamplePipeline | None = None,
        target_selection: GazeTargetSelectionPipeline | None = None,
        diagnostics: ScalarDiagnostics | None = None,
        heatmap: HeatmapOverlay | None = None,
        feedback: FeedbackSurface | None = None,
        calibration_store: CalibrationProfileStore | None = None,
    ) -> None:
        self._overlay = overlay
        self._activation = activation
        self._calibration_session = calibration_session
        self._calibration = CalibrationOnboardingController(session=calibration_session)
        self._sample_source = sample_source
        self._window_provider = window_provider
        self._display_provider = display_provider
        self._gaze_pipeline = gaze_pipeline or GazeSamplePipeline()
        self._target_selection = target_selection or GazeTargetSelectionPipeline()
        self._diagnostics = diagnostics or ScalarDiagnostics(profile=DiagnosticsProfile.release())
        self._heatmap = heatmap
        self._feedback = feedback
        self._calibration_store = calibration_store
        self._restored_calibration_pending_fresh_sample = False
        self.state = GazeAppState.default()
        self._restore_last_good_calibration()

    def enable_gaze(self) -> None:
        """Enable trust preview without implicitly starting camera calibration."""

        enabled = replace(self.state, flags=replace(self.state.flags, gaze_enabled=True))
        if not enabled.readiness.can_track:
            enabled = replace(enabled, last_status_message="Calibration required")
        else:
            enabled = replace(enabled, last_status_message="Gaze ready")
        self.state = enabled

    def disable_gaze(self) -> None:
        """Panic-disable tracking, overlays, and activation."""

        self.state = self.state.disable_panic()
        self._overlay.hide()
        if self._heatmap is not None:
            self._heatmap.hide()

    def start_calibration(self) -> None:
        """Run user-initiated calibration through the just-in-time session seam."""

        calibrating = self._calibration.begin(self.state)
        result = self._calibration_session.start()
        self.state = self._calibration.finish(calibrating, result)
        self._restored_calibration_pending_fresh_sample = False
        if self._calibration_store is not None:
            self._calibration_store.save(result)
        self._overlay.hide()

    def calibration_snapshot(self) -> CalibrationProviderSnapshot | None:
        """Return provider wizard state without starting camera or calibration."""

        snapshot = getattr(self._calibration_session, "snapshot", None)
        if snapshot is None:
            return None
        candidate = snapshot()
        if isinstance(candidate, CalibrationProviderSnapshot):
            return candidate
        return None

    def toggle_border_enabled(self) -> None:
        """Toggle the target border without changing calibration or gaze state."""

        enabled = not self.state.flags.target_border_enabled
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, target_border_enabled=enabled),
            overlay_visible=self.state.overlay_visible and enabled,
            last_status_message=("Target border on" if enabled else "Target border off"),
        )
        if not enabled:
            self._overlay.hide()

    def toggle_heatmap_enabled(self) -> None:
        """Toggle heatmap visibility or report that the runtime has no overlay."""

        if self._heatmap is None:
            self.state = replace(
                self.state,
                flags=replace(self.state.flags, heatmap_enabled=False),
                last_status_message="Heatmap unavailable",
            )
            return
        enabled = not self.state.flags.heatmap_enabled
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, heatmap_enabled=enabled),
            last_status_message=("Heatmap on" if enabled else "Heatmap off"),
        )
        if enabled:
            self._heatmap.show()
        else:
            self._heatmap.hide()

    def clear_heatmap_session(self) -> None:
        """Clear optional session-local heatmap data without hiding it."""

        if self._heatmap is not None:
            self._heatmap.clear()
        self.state = replace(self.state, last_status_message="Heatmap cleared")

    def tick(self, *, now_seconds: float, now_ms: int) -> None:
        """Advance one real trust-preview frame using scalar-only runtime data."""

        if not self.state.flags.gaze_enabled:
            self.state = replace(self.state, current_target=None, overlay_visible=False)
            self._overlay.hide()
            self._diagnostics.record_state(self.state, now_ms=now_ms)
            return

        if self.state.readiness.calibration in {
            CalibrationStatus.READY,
            CalibrationStatus.DEGRADED,
        }:
            previous_message = self.state.last_status_message
            self.state = self.state.with_current_display_layout(
                self._display_provider.current_layout()
            )
            display_layout_changed = self.state.last_status_message != previous_message
            if display_layout_changed:
                self._diagnostics.record_display_layout_degraded()
            if display_layout_changed and self.state.current_target is None:
                self._overlay.hide()
                self._diagnostics.record_state(self.state, now_ms=now_ms)
                return

        restored_degraded = self._restored_calibration_pending_fresh_sample
        sample = self._sample_source.current_sample()
        if sample is None:
            self.state = self.state.with_target(None)
            self._overlay.hide()
            self._diagnostics.record_state(self.state, now_ms=now_ms)
            return

        if self.state.readiness.calibration in {
            CalibrationStatus.CALIBRATING,
            CalibrationStatus.NOT_READY,
        } and self._sample_can_restore_tracking(sample, now_seconds=now_seconds):
            layout = self._display_provider.current_layout()
            self.state = replace(
                self.state,
                readiness=replace(
                    self.state.readiness,
                    calibration=CalibrationStatus.READY,
                    camera_available=True,
                    tracker_available=True,
                ),
                calibration_display_layout=layout,
                last_status_message="Calibration ready",
            )

        self.state = self._gaze_pipeline.apply(
            self.state,
            sample,
            now_seconds=now_seconds,
        )
        if self.state.current_gaze_sample is None or not self.state.current_gaze_sample.valid:
            self._overlay.hide()
            self._diagnostics.record_state(self.state, now_ms=now_ms)
            return
        current_gaze_sample = self.state.current_gaze_sample
        if restored_degraded:
            self.state = replace(
                self.state,
                readiness=replace(
                    self.state.readiness,
                    calibration=CalibrationStatus.READY,
                ),
            )
            self._restored_calibration_pending_fresh_sample = False
        if self.state.flags.heatmap_enabled and self._heatmap is not None:
            self._heatmap.show()
            self._heatmap.add_point(
                HeatmapPoint(
                    x=current_gaze_sample.x,
                    y=current_gaze_sample.y,
                    confidence=current_gaze_sample.confidence,
                )
            )

        candidates = self._targetable_candidates(self._window_provider.current_candidates())
        self.state = self._target_selection.apply(self.state, candidates, now_ms=now_ms)
        self._sync_overlay(candidates)
        self._diagnostics.record_state(self.state, now_ms=now_ms)

    def activate(self) -> ActivationOutcome:
        """Activate the locked target owning app through the activation service."""

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
        self._diagnostics.record_activation(outcome)
        if self._feedback is not None:
            self._feedback.show(feedback_for_activation(outcome))
        return outcome

    def _restore_last_good_calibration(self) -> None:
        if self._calibration_store is None:
            return
        restored = self._calibration_store.restore_for_layout(
            self._display_provider.current_layout()
        )
        if restored is None:
            return
        self.state = self._calibration.finish(self.state, restored)
        self._restored_calibration_pending_fresh_sample = True

    def _targetable_candidates(
        self,
        candidates: tuple[WindowCandidateSummary, ...],
    ) -> tuple[WindowCandidateSummary, ...]:
        ignored_owner_process_ids = _ignored_owner_process_ids(self._calibration_session)
        if not ignored_owner_process_ids:
            return candidates
        return tuple(
            candidate
            for candidate in candidates
            if candidate.owner_process_id not in ignored_owner_process_ids
        )

    def _sync_overlay(self, candidates: tuple[WindowCandidateSummary, ...]) -> None:
        if not (
            self.state.flags.gaze_enabled
            and self.state.flags.target_border_enabled
            and self.state.current_target is not None
            and self.state.current_target.locked
            and self.state.current_gaze_sample is not None
            and self.state.current_gaze_sample.valid
        ):
            self._overlay.hide()
            return

        candidate = candidate_at_gaze_point(self.state.current_gaze_sample, candidates)
        if candidate is None:
            self._overlay.hide()
            return
        self._overlay.show(candidate)

    def _sample_can_restore_tracking(
        self,
        sample: PupilTrackerGazeSample,
        *,
        now_seconds: float,
    ) -> bool:
        if not sample.valid:
            return False
        if sample.confidence < self._gaze_pipeline.min_confidence:
            return False
        return now_seconds - sample.timestamp <= self._gaze_pipeline.max_sample_age_seconds


def _ignored_owner_process_ids(source: object) -> frozenset[int]:
    provider = getattr(source, "ignored_owner_process_ids", None)
    if not callable(provider):
        return frozenset()
    raw_ids = cast(Any, provider)()
    if not isinstance(raw_ids, Iterable):
        return frozenset()
    return frozenset(pid for pid in raw_ids if isinstance(pid, int))
