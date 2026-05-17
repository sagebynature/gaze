"""Setup and calibration wizard window models for the trust-first MVP."""

from __future__ import annotations

from dataclasses import dataclass

from gaze.core.state import CalibrationStatus
from gaze.tracking.calibration import CalibrationProviderSnapshot, CalibrationStage

WINDOW_TITLE = "Gaze"


@dataclass(frozen=True)
class SetupSection:
    label: str
    description: str
    action: str | None = None


@dataclass(frozen=True)
class CalibrationWizardStep:
    label: str
    description: str
    state: str
    detail: str = ""


def setup_sections() -> list[SetupSection]:
    return [
        SetupSection(
            "Privacy & Trust",
            "No recording, no screenshots, no clicks, manual activation only.",
        ),
        SetupSection("Calibration", "Start or retry calibration just in time.", "recalibrate"),
        SetupSection("Hotkeys", "Edit Cmd+G activation and Option+Cmd+G toggle.", "hotkeys"),
        SetupSection("Border", "Control target border preview."),
        SetupSection("Heatmap", "Optional session-local diagnostic overlay."),
        SetupSection("Diagnostics", "Scalar-only diagnostics profile."),
    ]


def default_calibration_wizard_snapshot() -> CalibrationProviderSnapshot:
    return CalibrationProviderSnapshot(
        stage=CalibrationStage.PRIVACY,
        message="Private by design",
        progress=0.0,
    )


def calibration_wizard_steps(snapshot: CalibrationProviderSnapshot) -> list[CalibrationWizardStep]:
    active_index = _active_step_index(snapshot)
    return [
        CalibrationWizardStep(
            "Privacy",
            "Camera access starts only when you ask to calibrate.",
            _step_state(0, active_index),
            "No recording or screenshots.",
        ),
        CalibrationWizardStep(
            "Readiness",
            "Gaze checks camera and tracker readiness without saving visual content.",
            _step_state(1, active_index),
            _readiness_detail(snapshot),
        ),
        CalibrationWizardStep(
            "Calibration Targets",
            "Follow each target calmly; Gaze stores only scalar calibration quality.",
            _step_state(2, active_index),
            _target_detail(snapshot),
        ),
        CalibrationWizardStep(
            "Result",
            "Ready, degraded, and retry states stay understandable without developer details.",
            _step_state(3, active_index),
            _result_detail(snapshot),
        ),
    ]


def render_calibration_wizard_text(snapshot: CalibrationProviderSnapshot) -> str:
    lines = [
        "Gaze Calibration",
        "",
        "No recording, screenshots, window titles, URLs, filenames, or desktop content are saved.",
        "Camera access starts only when you ask to calibrate.",
        "",
    ]
    for step in calibration_wizard_steps(snapshot):
        marker = {"complete": "✓", "current": "→", "pending": "·"}[step.state]
        lines.append(f"{marker} {step.label}")
        lines.append(step.description)
        if step.detail:
            lines.append(step.detail)
        lines.append("")
    lines.append(f"Status: {_safe_status(snapshot)}")
    lines.append("Action: Recalibrate")
    return "\n".join(lines).strip()


def _active_step_index(snapshot: CalibrationProviderSnapshot) -> int:
    if snapshot.stage == CalibrationStage.PRIVACY:
        return 0
    if snapshot.stage == CalibrationStage.READINESS:
        return 1
    if snapshot.stage == CalibrationStage.TARGET_SEQUENCE:
        return 2
    return 3


def _step_state(index: int, active_index: int) -> str:
    if index < active_index:
        return "complete"
    if index == active_index:
        return "current"
    return "pending"


def _readiness_detail(snapshot: CalibrationProviderSnapshot) -> str:
    camera = "camera ready" if snapshot.camera_available else "camera pending"
    tracker = "tracker ready" if snapshot.tracker_available else "tracker pending"
    return f"{camera}; {tracker}"


def _target_detail(snapshot: CalibrationProviderSnapshot) -> str:
    if snapshot.current_target is None:
        if snapshot.stage == CalibrationStage.TARGET_SEQUENCE:
            return "Target sequence starting"
        return "Target sequence pending"
    return f"Target {snapshot.current_target.index} of {snapshot.current_target.total}"


def _result_detail(snapshot: CalibrationProviderSnapshot) -> str:
    if snapshot.result_status == CalibrationStatus.READY:
        return "Ready for daily use"
    if snapshot.result_status == CalibrationStatus.DEGRADED:
        return "Usable, but recalibration is recommended"
    if snapshot.result_status == CalibrationStatus.RETRY_REQUIRED:
        return "Try calibration again"
    if snapshot.stage == CalibrationStage.UNAVAILABLE:
        return "Calibration provider unavailable"
    return "Result pending"


def _safe_status(snapshot: CalibrationProviderSnapshot) -> str:
    if snapshot.stage == CalibrationStage.UNAVAILABLE:
        return "Calibration provider unavailable"
    if snapshot.result_status is not None:
        return snapshot.result_status.value
    return snapshot.message
