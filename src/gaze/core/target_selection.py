"""Pure gaze-point to visible-window target selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from gaze.core.state import GazeAppState, GazeSampleSummary, TargetSummary
from gaze.core.target_lock import TargetLockPolicy, TargetObservation
from gaze.desktop.window_candidates import WindowCandidateSummary


@dataclass(frozen=True)
class GazeTargetSelectionPipeline:
    """Select and lock a visible window candidate from the current gaze point."""

    stability_ms: int = 400
    _lock: TargetLockPolicy = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.stability_ms < 0:
            msg = "stability_ms must be non-negative"
            raise ValueError(msg)
        object.__setattr__(self, "_lock", TargetLockPolicy(stability_ms=self.stability_ms))

    def apply(
        self,
        state: GazeAppState,
        candidates: Sequence[WindowCandidateSummary],
        *,
        now_ms: int,
    ) -> GazeAppState:
        """Apply one candidate-selection tick to immutable app state."""

        sample = state.current_gaze_sample
        if sample is None or not sample.valid:
            self._lock.update(None, now_ms=now_ms)
            return state.with_target(None)

        candidate = candidate_at_gaze_point(sample, candidates)
        if candidate is None:
            self._lock.update(None, now_ms=now_ms)
            return state.with_target(None)

        lock = self._lock.update(
            TargetObservation(app_name=candidate.app_name, confidence=candidate.confidence),
            now_ms=now_ms,
        )
        if not lock.locked:
            return state.with_target(None)

        return state.with_target(
            TargetSummary(
                app_name=candidate.app_name,
                confidence=candidate.confidence,
                locked=True,
            )
        )


def candidate_at_gaze_point(
    sample: GazeSampleSummary,
    candidates: Sequence[WindowCandidateSummary],
) -> WindowCandidateSummary | None:
    """Return the topmost candidate containing the valid gaze sample point."""

    if not sample.valid:
        return None
    return next((candidate for candidate in candidates if _contains_point(candidate, sample)), None)


def _contains_point(candidate: WindowCandidateSummary, sample: GazeSampleSummary) -> bool:
    min_x = candidate.bounds_x
    min_y = candidate.bounds_y
    max_x = candidate.bounds_x + candidate.bounds_width
    max_y = candidate.bounds_y + candidate.bounds_height
    return min_x <= sample.x < max_x and min_y <= sample.y < max_y
