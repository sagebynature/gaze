"""Core app state for safe gaze-assisted activation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CalibrationStatus(StrEnum):
    """User-facing calibration readiness."""

    NOT_READY = "not_ready"
    CALIBRATING = "calibrating"
    READY = "ready"
    DEGRADED = "degraded"
    RETRY_REQUIRED = "retry_required"


@dataclass(frozen=True)
class GazeFeatureFlags:
    """User-controlled feature switches.

    Manual activation is the MVP path. Auto-activation stays disabled unless a
    later product decision explicitly enables it.
    """

    gaze_enabled: bool = False
    target_border_enabled: bool = True
    heatmap_enabled: bool = False
    auto_activate_enabled: bool = False


@dataclass(frozen=True)
class GazeReadiness:
    """Current readiness state for the app shell."""

    calibration: CalibrationStatus = CalibrationStatus.NOT_READY
    camera_available: bool = False
    tracker_available: bool = False

    @property
    def can_track(self) -> bool:
        """Return whether live gaze tracking may run."""

        return (
            self.camera_available
            and self.tracker_available
            and self.calibration in {CalibrationStatus.READY, CalibrationStatus.DEGRADED}
        )


def manual_activation_allowed(flags: GazeFeatureFlags, readiness: GazeReadiness) -> bool:
    """Return whether Cmd+G is allowed to request target activation."""

    return flags.gaze_enabled and readiness.can_track
