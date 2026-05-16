"""Setup window model for the trust-first MVP."""

from __future__ import annotations

from dataclasses import dataclass

WINDOW_TITLE = "Gaze"


@dataclass(frozen=True)
class SetupSection:
    label: str
    description: str


def setup_sections() -> list[SetupSection]:
    return [
        SetupSection(
            "Privacy & Trust",
            "No recording, no screenshots, no clicks, manual activation only.",
        ),
        SetupSection("Calibration", "Start or retry calibration just in time."),
        SetupSection("Hotkeys", "Edit Cmd+G activation and Option+Cmd+G toggle."),
        SetupSection("Border", "Control target border preview."),
        SetupSection("Heatmap", "Optional session-local diagnostic overlay."),
        SetupSection("Diagnostics", "Scalar-only diagnostics profile."),
    ]
