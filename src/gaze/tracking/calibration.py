"""Just-in-time calibration onboarding seams.

This module is deliberately import-safe: it defines pure state transitions and a
small session protocol, but it does not import PupilTracker, AppKit, camera
libraries, or start any hardware work at import time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Protocol

from gaze.core.display_geometry import DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus, GazeAppState, GazeReadiness

ScalarValue = str | int | float | bool | None
_ALLOWED_CALIBRATION_SNAPSHOT_MESSAGES = frozenset(
    {
        "Private by design",
        "Checking camera",
        "Camera ready",
        "Follow the target",
        "Ready",
        "Try calibration again",
        "Camera unavailable",
        "Legacy PupilTracker desktop demo provider idle",
        "Calibration provider unavailable",
        "PupilTracker calibration launched",
    }
)
_ALLOWED_CALIBRATION_EXTRA_FIELDS = frozenset(
    {
        "sample_count",
        "target_count",
        "accepted_sample_count",
        "rejected_sample_count",
        "elapsed_ms",
    }
)
_ALLOWED_CALIBRATION_QUALITY_FIELDS = frozenset(
    {
        "mean_error_px",
        "max_error_px",
        "accepted_sample_count",
        "rejected_sample_count",
        "recommendation",
    }
)
_ALLOWED_CALIBRATION_RECOMMENDATIONS = frozenset({"excellent", "good", "usable", "retry"})
_CALIBRATION_INTEGER_FIELDS = frozenset(
    {
        "sample_count",
        "target_count",
        "accepted_sample_count",
        "rejected_sample_count",
    }
)
_CALIBRATION_NUMBER_FIELDS = frozenset({"elapsed_ms", "mean_error_px", "max_error_px"})
_RESERVED_CALIBRATION_PAYLOAD_FIELDS = frozenset(
    {
        "stage",
        "message",
        "camera_available",
        "tracker_available",
        "current_target",
        "progress",
        "quality",
        "result_status",
    }
)
_FORBIDDEN_CALIBRATION_PAYLOAD_TOKENS = frozenset(
    {
        "title",
        "url",
        "filename",
        "file",
        "document",
        "screenshot",
        "camera",
        "frame",
        "image",
        "desktop",
        "visual",
        "video",
        "path",
        "bytes",
    }
)


class CalibrationStage(StrEnum):
    """UI-safe stage names for a Gaze-owned calibration provider."""

    PRIVACY = "privacy"
    READINESS = "readiness"
    TARGET_SEQUENCE = "target_sequence"
    RESULT = "result"
    RETRY_REQUIRED = "retry_required"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class CalibrationTargetPoint:
    """Scalar-only normalized target point for the Gaze-owned wizard."""

    x: float
    y: float
    index: int
    total: int

    def __post_init__(self) -> None:
        if not _is_finite_number(self.x):
            raise ValueError("calibration target x must be finite")
        if not _is_finite_number(self.y):
            raise ValueError("calibration target y must be finite")
        if not 0 <= self.x <= 1:
            raise ValueError("calibration target x must be normalized")
        if not 0 <= self.y <= 1:
            raise ValueError("calibration target y must be normalized")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 1:
            raise ValueError("calibration target index must be a positive integer")
        if (
            isinstance(self.total, bool)
            or not isinstance(self.total, int)
            or self.total < self.index
        ):
            raise ValueError("calibration target total must cover index")

    def to_scalar_payload(self) -> dict[str, ScalarValue]:
        return {"x": self.x, "y": self.y, "index": self.index, "total": self.total}


@dataclass(frozen=True)
class CalibrationProviderSnapshot:
    """Scalar-only snapshot of a Gaze-owned calibration provider."""

    stage: CalibrationStage
    message: str
    camera_available: bool = False
    tracker_available: bool = False
    current_target: CalibrationTargetPoint | None = None
    progress: float = 0.0
    quality: Mapping[str, ScalarValue] | None = None
    result_status: CalibrationStatus | None = None
    extra_scalars: Mapping[str, ScalarValue] | None = None

    def __post_init__(self) -> None:
        _validate_snapshot_fixed_fields(self)
        if not 0 <= self.progress <= 1:
            raise ValueError("calibration progress must be normalized")
        _validate_snapshot_message(self.message)
        quality = dict(self.quality or {})
        extra_scalars = dict(self.extra_scalars or {})
        _validate_scalar_payload(quality, allowed_fields=_ALLOWED_CALIBRATION_QUALITY_FIELDS)
        _validate_scalar_payload(
            extra_scalars,
            reject_reserved=True,
            allowed_fields=_ALLOWED_CALIBRATION_EXTRA_FIELDS,
        )
        object.__setattr__(self, "quality", MappingProxyType(quality) if quality else None)
        object.__setattr__(
            self,
            "extra_scalars",
            MappingProxyType(extra_scalars) if extra_scalars else None,
        )

    def to_scalar_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "stage": self.stage.value,
            "message": self.message,
            "camera_available": self.camera_available,
            "tracker_available": self.tracker_available,
            "current_target": (
                self.current_target.to_scalar_payload() if self.current_target is not None else None
            ),
            "progress": self.progress,
            "quality": dict(self.quality) if self.quality is not None else None,
            "result_status": self.result_status.value if self.result_status is not None else None,
        }
        if self.extra_scalars:
            payload.update(self.extra_scalars)
        return payload


class CalibrationProvider(Protocol):
    """UI-owned calibration provider boundary for Gaze product flows."""

    def start(self) -> CalibrationResult:
        """Start provider-side calibration resources only after explicit user action."""
        ...

    def snapshot(self) -> CalibrationProviderSnapshot:
        """Return the latest scalar-only provider snapshot for the wizard UI."""
        ...


def _is_finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float) and isfinite(float(value))


def _validate_snapshot_fixed_fields(snapshot: CalibrationProviderSnapshot) -> None:
    if not isinstance(snapshot.stage, CalibrationStage):
        raise ValueError("stage must be CalibrationStage")
    if not isinstance(snapshot.message, str):
        raise ValueError("message must be str")
    if not isinstance(snapshot.camera_available, bool):
        raise ValueError("camera_available must be bool")
    if not isinstance(snapshot.tracker_available, bool):
        raise ValueError("tracker_available must be bool")
    if snapshot.current_target is not None and not isinstance(
        snapshot.current_target,
        CalibrationTargetPoint,
    ):
        raise ValueError("current_target must be CalibrationTargetPoint")
    if not _is_finite_number(snapshot.progress):
        raise ValueError("progress must be a finite number")
    if snapshot.result_status is not None and not isinstance(
        snapshot.result_status,
        CalibrationStatus,
    ):
        raise ValueError("result_status must be CalibrationStatus")


def _validate_snapshot_message(message: str) -> None:
    if message not in _ALLOWED_CALIBRATION_SNAPSHOT_MESSAGES:
        raise ValueError("forbidden calibration snapshot message")


def _validate_scalar_payload(
    payload: Mapping[str, ScalarValue],
    *,
    reject_reserved: bool = False,
    allowed_fields: frozenset[str] | None = None,
) -> None:
    for key, value in payload.items():
        normalized_key = _normalize_payload_key(key)
        if reject_reserved and normalized_key in _RESERVED_CALIBRATION_PAYLOAD_FIELDS:
            raise ValueError(f"reserved calibration payload field: {key}")
        if any(token in normalized_key for token in _FORBIDDEN_CALIBRATION_PAYLOAD_TOKENS):
            raise ValueError(f"forbidden calibration payload field: {key}")
        if allowed_fields is not None and normalized_key not in allowed_fields:
            raise ValueError(f"unsupported calibration payload field: {key}")
        _validate_scalar_payload_value(key=key, normalized_key=normalized_key, value=value)


def _validate_scalar_payload_value(
    *,
    key: str,
    normalized_key: str,
    value: ScalarValue,
) -> None:
    if normalized_key in _CALIBRATION_INTEGER_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"calibration payload field must be a non-negative integer: {key}")
        return
    if normalized_key in _CALIBRATION_NUMBER_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(
                f"calibration payload field must be a finite non-negative number: {key}"
            )
        if value < 0 or not isfinite(float(value)):
            raise ValueError(
                f"calibration payload field must be a finite non-negative number: {key}"
            )
        return
    if normalized_key == "recommendation":
        if not isinstance(value, str) or value not in _ALLOWED_CALIBRATION_RECOMMENDATIONS:
            raise ValueError(f"unsupported calibration recommendation: {key}")
        return
    if not isinstance(value, str | int | float | bool | type(None)):
        raise ValueError(f"calibration payload field must be scalar: {key}")


def _normalize_payload_key(key: str) -> str:
    normalized = ""
    for character in key:
        if character.isupper():
            normalized += f"_{character.lower()}"
        elif character.isalnum():
            normalized += character.lower()
        else:
            normalized += "_"
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


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
