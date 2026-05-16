"""Just-in-time calibration onboarding seams.

This module is deliberately import-safe: it defines pure state transitions and a
small session protocol, but it does not import PupilTracker, AppKit, camera
libraries, or start any hardware work at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from gaze.core.display_geometry import DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus, GazeAppState, GazeReadiness


@dataclass(frozen=True)
class CalibrationResult:
    """Result returned by a calibration session after user-initiated start."""

    status: CalibrationStatus
    message: str
    camera_available: bool = True
    tracker_available: bool = True
    display_layout: DisplayLayoutSnapshot | None = None

    @classmethod
    def ready(
        cls,
        message: str = "Calibration ready",
        *,
        display_layout: DisplayLayoutSnapshot | None = None,
    ) -> CalibrationResult:
        return cls(
            status=CalibrationStatus.READY,
            message=message,
            display_layout=display_layout,
        )

    @classmethod
    def degraded(cls, message: str = "Calibration degraded") -> CalibrationResult:
        return cls(status=CalibrationStatus.DEGRADED, message=message)

    @classmethod
    def retry_required(cls, message: str = "Calibration retry required") -> CalibrationResult:
        return cls(status=CalibrationStatus.RETRY_REQUIRED, message=message)

    @classmethod
    def unavailable(cls, message: str = "Calibration unavailable") -> CalibrationResult:
        return cls(
            status=CalibrationStatus.RETRY_REQUIRED,
            message=message,
            camera_available=False,
            tracker_available=False,
        )


class CalibrationSession(Protocol):
    """Side-effecting calibration session boundary.

    Implementations may request camera permission, open a calibration UI, or call
    into PupilTracker, but only when ``start`` is invoked by an explicit user
    action.
    """

    def start(self) -> CalibrationResult:
        """Start calibration and return the resulting readiness."""
        ...


class CalibrationOnboardingController:
    """Pure state coordinator for just-in-time calibration onboarding."""

    def __init__(self, *, session: CalibrationSession) -> None:
        self._session = session

    def begin(self, state: GazeAppState) -> GazeAppState:
        """Enter calibrating state without touching camera/session resources."""

        cleared = state.with_target(None)
        return replace(
            cleared,
            readiness=replace(cleared.readiness, calibration=CalibrationStatus.CALIBRATING),
            last_status_message="Calibrating",
        )

    def finish(self, state: GazeAppState, result: CalibrationResult) -> GazeAppState:
        """Apply a completed calibration result to app state."""

        cleared = state.with_target(None)
        return replace(
            cleared,
            readiness=GazeReadiness(
                calibration=result.status,
                camera_available=result.camera_available,
                tracker_available=result.tracker_available,
            ),
            calibration_display_layout=result.display_layout,
            last_status_message=result.message,
        )

    def run(self, state: GazeAppState) -> GazeAppState:
        """Start calibration just in time and return final state."""

        calibrating = self.begin(state)
        result = self._session.start()
        return self.finish(calibrating, result)
