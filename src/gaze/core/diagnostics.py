"""Scalar-only diagnostics for local tuning evidence.

Diagnostics are intentionally constrained to counters and scalar state. They must
never include screenshots, frames, window titles, app names, or raw desktop
content.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeAlias, TypeGuard

from gaze.core.state import GazeAppState
from gaze.desktop.activation import ActivationOutcome

ScalarValue: TypeAlias = bool | int | float | str | None

_CONTENT_KEYS = frozenset(
    {
        "app_name",
        "frame",
        "image",
        "pixels",
        "raw_content",
        "screenshot",
        "title",
        "window_title",
    }
)

_SCALAR_SUMMARY_KEYS = frozenset(
    {
        "enabled",
        "calibration_state",
        "last_confidence",
        "target_locked",
        "lock_duration_ms",
        "last_activation_result",
        "already_frontmost_count",
        "no_target_count",
        "display_layout_degraded_events",
        "hotkey_registration_status",
        "hotkey_registration_issue_count",
    }
)


@dataclass(frozen=True)
class DiagnosticsProfile:
    """Runtime diagnostics posture."""

    enabled: bool

    @classmethod
    def dev(cls) -> DiagnosticsProfile:
        return cls(enabled=True)

    @classmethod
    def release(cls) -> DiagnosticsProfile:
        return cls(enabled=False)


def default_diagnostics_profile(*, development_mode: bool) -> DiagnosticsProfile:
    return DiagnosticsProfile.dev() if development_mode else DiagnosticsProfile.release()


def export_scalar_summary_json(
    snapshot: Mapping[str, object],
    *,
    checklist_id: str = "gaze-beta-ready-manual-validation",
) -> str:
    """Export a deterministic content-safe scalar diagnostics summary."""

    summary: dict[str, ScalarValue] = {}
    for key, value in snapshot.items():
        if not _is_scalar(value):
            msg = "scalar summary exports must be scalar-only"
            raise ValueError(msg)
        if _content_like_key(key):
            msg = "scalar summary exports must not include content fields"
            raise ValueError(msg)
        if key not in _SCALAR_SUMMARY_KEYS:
            msg = "scalar summary exports must not include unsupported fields"
            raise ValueError(msg)
        summary[key] = value
    return json.dumps(
        {
            "checklist_id": checklist_id,
            "schema_version": "gaze.scalar-summary.v1",
            "summary": summary,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass
class ScalarDiagnostics:
    """Small scalar diagnostics accumulator for local validation."""

    profile: DiagnosticsProfile
    _last_confidence: float | None = None
    _calibration_state: str | None = None
    _target_locked: bool = False
    _lock_started_ms: int | None = None
    _lock_duration_ms: int = 0
    _last_activation_result: str | None = None
    _already_frontmost_count: int = 0
    _no_target_count: int = 0
    _display_layout_degraded_events: int = 0
    _hotkey_registration_status: str = "ok"
    _hotkey_registration_issue_count: int = 0
    _payloads: dict[str, ScalarValue] = field(default_factory=dict)

    def record_state(self, state: GazeAppState, *, now_ms: int) -> None:
        if not self.profile.enabled:
            return
        self._calibration_state = state.readiness.calibration.value
        if state.current_gaze_sample is not None:
            self._last_confidence = state.current_gaze_sample.confidence
        locked = state.current_target is not None and state.current_target.locked
        if locked and not self._target_locked:
            self._lock_started_ms = now_ms
            self._lock_duration_ms = 0
        elif locked and self._lock_started_ms is not None:
            self._lock_duration_ms = max(0, now_ms - self._lock_started_ms)
        elif not locked:
            self._lock_started_ms = None
            self._lock_duration_ms = 0
        self._target_locked = locked

    def record_activation(self, outcome: ActivationOutcome) -> None:
        if not self.profile.enabled:
            return
        self._last_activation_result = outcome.value
        if outcome == ActivationOutcome.ALREADY_FRONTMOST:
            self._already_frontmost_count += 1
        if outcome == ActivationOutcome.NO_TARGET:
            self._no_target_count += 1

    def record_display_layout_degraded(self) -> None:
        if not self.profile.enabled:
            return
        self._display_layout_degraded_events += 1

    def record_hotkey_feedback(self, feedback_messages: tuple[str, ...]) -> None:
        if not self.profile.enabled:
            return
        self._hotkey_registration_issue_count = len(feedback_messages)
        self._hotkey_registration_status = "issues" if feedback_messages else "ok"

    def record_payload(self, event_name: str, payload: dict[str, object]) -> None:
        if not self.profile.enabled:
            return
        for key, value in payload.items():
            if not _is_scalar(value):
                msg = "diagnostics payloads must be scalar-only"
                raise ValueError(msg)
            if _content_like_key(key):
                msg = "diagnostics payloads must not include content fields"
                raise ValueError(msg)
            self._payloads[f"{event_name}.{key}"] = value

    def snapshot(self) -> dict[str, ScalarValue]:
        if not self.profile.enabled:
            return {"enabled": False}
        snapshot: dict[str, ScalarValue] = {
            "enabled": True,
            "calibration_state": self._calibration_state,
            "last_confidence": self._last_confidence,
            "target_locked": self._target_locked,
            "lock_duration_ms": self._lock_duration_ms,
            "last_activation_result": self._last_activation_result,
            "already_frontmost_count": self._already_frontmost_count,
            "no_target_count": self._no_target_count,
            "display_layout_degraded_events": self._display_layout_degraded_events,
            "hotkey_registration_status": self._hotkey_registration_status,
            "hotkey_registration_issue_count": self._hotkey_registration_issue_count,
        }
        snapshot.update(self._payloads)
        return snapshot


def _is_scalar(value: object) -> TypeGuard[ScalarValue]:
    return value is None or isinstance(value, bool | int | float | str)


def _content_like_key(key: str) -> bool:
    normalized = key.lower()
    return any(content_key in normalized for content_key in _CONTENT_KEYS)
