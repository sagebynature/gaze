"""Import-safe PupilTracker gaze sample to app-state pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from gaze.core.state import GazeAppState, GazeSampleSummary


class PupilTrackerGazeSample(Protocol):
    """Minimal shape consumed from PupilTracker gaze samples."""

    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool


@dataclass(frozen=True)
class GazeSamplePipeline:
    """Convert PupilTracker-like gaze samples into app-level gaze state."""

    min_confidence: float = 0.60
    max_sample_age_seconds: float = 0.25

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            msg = "min_confidence must be between 0 and 1"
            raise ValueError(msg)
        if self.max_sample_age_seconds <= 0:
            msg = "max_sample_age_seconds must be positive"
            raise ValueError(msg)

    def apply(
        self,
        state: GazeAppState,
        sample: PupilTrackerGazeSample,
        *,
        now_seconds: float,
    ) -> GazeAppState:
        """Apply one PupilTracker sample to immutable app state."""

        if not state.flags.gaze_enabled or not state.readiness.can_track:
            return state.with_gaze_sample(self._rejected_sample(sample, "tracking not ready"))
        if not sample.valid:
            reason = getattr(sample, "reason", None) or "invalid sample"
            return state.with_gaze_sample(self._rejected_sample(sample, reason))
        if sample.confidence < self.min_confidence:
            return state.with_gaze_sample(self._rejected_sample(sample, "low confidence"))
        if now_seconds - sample.timestamp > self.max_sample_age_seconds:
            return state.with_gaze_sample(self._rejected_sample(sample, "stale sample"))
        return state.with_gaze_sample(
            GazeSampleSummary(
                timestamp=sample.timestamp,
                x=sample.x,
                y=sample.y,
                confidence=sample.confidence,
                valid=True,
            )
        )

    @staticmethod
    def _rejected_sample(
        sample: PupilTrackerGazeSample,
        reason: str,
    ) -> GazeSampleSummary:
        return GazeSampleSummary(
            timestamp=sample.timestamp,
            x=sample.x,
            y=sample.y,
            confidence=sample.confidence,
            valid=False,
            reason=reason,
        )
