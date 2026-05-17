"""Core app state for safe gaze-assisted activation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from gaze.core.display_geometry import DisplayLayoutSnapshot


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
    auto_activate_debounce_ms: int = 650

    def __post_init__(self) -> None:
        if not 250 <= self.auto_activate_debounce_ms <= 2000:
            raise ValueError("auto-activate debounce must stay between 250ms and 2000ms")


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
    owner_process_id: int | None = None

    def __post_init__(self) -> None:
        if " - " in self.app_name:
            raise ValueError("target summary must use app name only")


@dataclass(frozen=True)
class GazeSampleSummary:
    """UI-safe app-level gaze sample with no frame or desktop content."""

    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool
    reason: str | None = None


@dataclass(frozen=True)
class GazeAppState:
    """Pure state snapshot for menu, overlay, and activation decisions."""

    flags: GazeFeatureFlags
    readiness: GazeReadiness
    current_target: TargetSummary | None = None
    current_gaze_sample: GazeSampleSummary | None = None
    overlay_visible: bool = False
    last_status_message: str = "Gaze off"
    calibration_display_layout: DisplayLayoutSnapshot | None = None

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
        if self.readiness.calibration == CalibrationStatus.RETRY_REQUIRED:
            return "retry_required"
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

    def with_gaze_sample(self, sample: GazeSampleSummary) -> GazeAppState:
        if sample.valid:
            return replace(
                self,
                current_gaze_sample=sample,
                last_status_message="Gaze sample ready",
            )

        reason = sample.reason or "invalid sample"
        degraded_readiness = self.readiness
        if self.readiness.can_track:
            degraded_readiness = replace(
                self.readiness,
                calibration=CalibrationStatus.DEGRADED,
            )
        return replace(
            self,
            readiness=degraded_readiness,
            current_gaze_sample=sample,
            current_target=None,
            overlay_visible=False,
            last_status_message=f"Gaze degraded: {reason}",
        )

    def with_current_display_layout(
        self,
        current_layout: DisplayLayoutSnapshot,
    ) -> GazeAppState:
        """Validate current layout against the layout used for calibration."""

        if self.calibration_display_layout is None:
            return replace(self, calibration_display_layout=current_layout)
        if self.calibration_display_layout.signature == current_layout.signature:
            return self
        if self.readiness.calibration not in {
            CalibrationStatus.READY,
            CalibrationStatus.DEGRADED,
        }:
            return self
        return replace(
            self,
            readiness=replace(self.readiness, calibration=CalibrationStatus.DEGRADED),
            current_target=None,
            overlay_visible=False,
            last_status_message="Display layout changed; recalibrate recommended",
        )

    def disable_panic(self) -> GazeAppState:
        return replace(
            self,
            flags=replace(self.flags, gaze_enabled=False),
            current_target=None,
            current_gaze_sample=None,
            overlay_visible=False,
            last_status_message="Gaze disabled",
        )
