"""Content-safe persistence for the last usable calibration posture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze.core.display_geometry import DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus
from gaze.tracking.calibration import CalibrationResult

_SCHEMA_VERSION = "gaze.last-good-calibration.v1"
_RESTORED_MESSAGE = "Calibration restored; fresh sample required"


class LastGoodCalibrationStore:
    """Persist a scalar-only last-good calibration record."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, result: CalibrationResult) -> None:
        """Save a usable calibration result without raw visual or desktop content."""

        if result.status not in {CalibrationStatus.READY, CalibrationStatus.DEGRADED}:
            return
        if result.display_layout is None:
            return
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "calibration_state": result.status.value,
            "display_layout_signature": result.display_layout.signature,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

    def restore_for_layout(self, current_layout: DisplayLayoutSnapshot) -> CalibrationResult | None:
        """Restore as degraded-but-usable only when display geometry still matches."""

        payload = self._read_payload()
        if payload is None:
            return None
        if payload.get("schema_version") != _SCHEMA_VERSION:
            return None
        if payload.get("display_layout_signature") != current_layout.signature:
            return None
        if payload.get("calibration_state") not in {
            CalibrationStatus.READY.value,
            CalibrationStatus.DEGRADED.value,
        }:
            return None
        return CalibrationResult(
            status=CalibrationStatus.DEGRADED,
            message=_RESTORED_MESSAGE,
            camera_available=True,
            tracker_available=True,
            display_layout=current_layout,
        )

    def _read_payload(self) -> dict[str, Any] | None:
        if not self._path.is_file():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if not all(isinstance(key, str) for key in payload):
            return None
        if not all(_is_scalar(value) for value in payload.values()):
            return None
        return payload


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, bool | int | float | str)
