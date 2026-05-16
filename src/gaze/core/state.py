"""Core app state for safe gaze-assisted activation."""

from __future__ import annotations

from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class TargetSummary:
    """UI-safe target summary. App name only; never a window title."""

    app_name: str
    confidence: float
    locked: bool

    def __post_init__(self) -> None:
        if " - " in self.app_name:
            raise ValueError("target summary must use app name only")


@dataclass(frozen=True)
class GazeAppState:
    """Pure state snapshot for menu, overlay, and activation decisions."""

    flags: GazeFeatureFlags
    readiness: GazeReadiness
    current_target: TargetSummary | None = None
    overlay_visible: bool = False
    last_status_message: str = "Gaze off"

    @classmethod
    def default(cls) -> GazeAppState:
        return cls(flags=GazeFeatureFlags(), readiness=GazeReadiness())

    @property
    def menu_status(self) -> str:
        if not self.flags.gaze_enabled:
            return "off"
        if self.readiness.calibration == CalibrationStatus.CALIBRATING:
            return "calibrating"
        if self.readiness.calibration == CalibrationStatus.DEGRADED:
            return "degraded"
        if manual_activation_allowed(self.flags, self.readiness):
            return "ready"
        return "not_ready"

    @property
    def activation_blocked(self) -> bool:
        return not (
            manual_activation_allowed(self.flags, self.readiness)
            and self.current_target is not None
            and self.current_target.locked
        )

    def with_target(self, target: TargetSummary | None) -> GazeAppState:
        return replace(
            self,
            current_target=target,
            overlay_visible=(
                self.flags.gaze_enabled
                and self.flags.target_border_enabled
                and target is not None
                and target.locked
            ),
            last_status_message="Target locked" if target and target.locked else "No target",
        )

    def disable_panic(self) -> GazeAppState:
        return replace(
            self,
            flags=replace(self.flags, gaze_enabled=False),
            current_target=None,
            overlay_visible=False,
            last_status_message="Gaze disabled",
        )
