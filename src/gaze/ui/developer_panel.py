"""Development-only panel model for fake prototype controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeveloperControl:
    label: str
    action: str


def developer_controls() -> list[DeveloperControl]:
    return [
        DeveloperControl("Start Scripted Demo", "start_scripted_demo"),
        DeveloperControl("Stop Scripted Demo", "stop_scripted_demo"),
        DeveloperControl("Set Fake Target", "set_fake_target"),
        DeveloperControl("Set Fake Target Bounds", "set_fake_target_bounds"),
        DeveloperControl("Set Fake Confidence", "set_fake_confidence"),
        DeveloperControl("Set Fake Lock State", "set_fake_lock_state"),
        DeveloperControl("Set Fake Frontmost App", "set_fake_frontmost_app"),
        DeveloperControl("Trigger Activation Success", "trigger_activation_success"),
        DeveloperControl("Trigger Activation Failure", "trigger_activation_failure"),
        DeveloperControl("Trigger No Target", "trigger_no_target"),
        DeveloperControl("Trigger Degraded", "trigger_degraded"),
    ]
