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


def settings_overview_sections() -> list[SetupSection]:
    """Return the private-beta Settings sections in user-facing order."""

    return [
        SetupSection(
            "Status Overview",
            "Gaze is off until you enable it. Calibration and target status stay visible here.",
        ),
        SetupSection(
            "Calibration",
            "Start or retry calibration only when you ask. Camera access starts just in time.",
            "recalibrate",
        ),
        SetupSection(
            "Gaze Control",
            "Enable or disable Gaze. Disable stops all activation and clears the current target.",
            "toggle_gaze",
        ),
        SetupSection(
            "Target Border",
            "Show the calm border preview around the locked app target, or keep it hidden.",
            "toggle_border",
        ),
        SetupSection(
            "Hotkeys",
            "Cmd+G remains available for manual activation; Option+Cmd+G toggles Gaze.",
            "hotkeys",
        ),
        SetupSection(
            "Auto-Activate",
            "Optional automation is off by default and waits for a stable locked target.",
            "toggle_auto_activate",
        ),
        SetupSection(
            "Activation Delay",
            "Bounded 250-2000ms delay before optional automation; manual Cmd+G stays immediate.",
            "set_auto_activate_debounce",
        ),
        SetupSection(
            "Privacy & Diagnostics",
            "Export scalar-only diagnostics. No app names, titles, paths, "
            "or visual content are included.",
            "export_scalar_summary",
        ),
        SetupSection(
            "Reset Calibration",
            "Clear the local scalar calibration profile and start fresh when the setup changes.",
            "reset_calibration",
        ),
    ]


def render_settings_overview_text() -> str:
    """Render a calm, content-safe Settings overview for the native text surface."""

    lines = [
        "Gaze Settings",
        "Private daily-driver controls for calibration, activation, and privacy.",
        "No screenshots, camera frames, window titles, URLs, filenames, or desktop content.",
        "",
    ]
    for section in settings_overview_sections():
        lines.append(f"• {section.label}")
        lines.append(section.description)
        if section.action is not None:
            lines.append(f"Action: {_action_title(section.action)}")
        lines.append("")
    return "\n".join(lines).strip()


def _action_title(action: str) -> str:
    return " ".join(word.capitalize() for word in action.split("_"))


def setup_sections() -> list[SetupSection]:
    return [
        SetupSection(
            "Privacy & Trust",
            "No recording, no screenshots, no clicks, manual activation by default.",
        ),
        SetupSection("Calibration", "Start or retry calibration just in time.", "recalibrate"),
        SetupSection("Gaze Control", "Enable or disable Gaze; disable stops all activation."),
        SetupSection(
            "Target Border",
            "Show or hide the calm target border preview.",
            "toggle_border",
        ),
        SetupSection("Hotkeys", "Edit Cmd+G activation and Option+Cmd+G toggle.", "hotkeys"),
        SetupSection(
            "Auto-Activate",
            "Off by default. Optional automation only after a locked target is stable.",
            "toggle_auto_activate",
        ),
        SetupSection(
            "Activation Delay",
            "Bounded debounce before optional auto-activation; Cmd+G stays available.",
            "set_auto_activate_debounce",
        ),
        SetupSection(
            "Privacy & Diagnostics",
            "Export scalar-only diagnostics without app names, titles, or content.",
            "export_scalar_summary",
        ),
        SetupSection(
            "Reset Calibration",
            "Clear local calibration and recalibrate.",
            "reset_calibration",
        ),
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
