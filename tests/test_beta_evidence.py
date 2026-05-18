from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaze.core.diagnostics import DiagnosticsProfile, ScalarDiagnostics, export_scalar_summary_json
from gaze.desktop.activation import ActivationOutcome


def test_scalar_summary_export_is_json_scalar_only_and_content_safe() -> None:
    diagnostics = ScalarDiagnostics(profile=DiagnosticsProfile.dev())
    diagnostics.record_activation(ActivationOutcome.ALREADY_FRONTMOST)
    diagnostics.record_activation(ActivationOutcome.NO_TARGET)
    diagnostics.record_display_layout_degraded()
    diagnostics.record_hotkey_feedback(("unavailable cmd+g for Activate Target",))

    exported = export_scalar_summary_json(
        diagnostics.snapshot(),
        checklist_id="gaze-beta-ready-manual-validation",
    )

    summary = json.loads(exported)
    assert summary == {
        "checklist_id": "gaze-beta-ready-manual-validation",
        "schema_version": "gaze.scalar-summary.v1",
        "summary": {
            "enabled": True,
            "calibration_state": None,
            "last_confidence": None,
            "target_locked": False,
            "lock_duration_ms": 0,
            "last_activation_result": "no_target",
            "already_frontmost_count": 1,
            "no_target_count": 1,
            "display_layout_degraded_events": 1,
            "hotkey_registration_status": "issues",
            "hotkey_registration_issue_count": 1,
        },
    }
    assert "cmd+g" not in exported
    assert "Activate Target" not in exported
    assert "Terminal" not in exported
    assert "window_title" not in exported
    assert "screenshot" not in exported
    assert "frame" not in exported


def test_scalar_summary_export_rejects_content_keys_and_non_scalar_values() -> None:
    with pytest.raises(ValueError, match="content fields"):
        export_scalar_summary_json({"window_title": "Secret"})

    with pytest.raises(ValueError, match="scalar-only"):
        export_scalar_summary_json({"enabled": True, "raw": {"nested": "value"}})

    with pytest.raises(ValueError, match="unsupported fields"):
        export_scalar_summary_json({"enabled": True, "app": "Terminal"})


def test_package_metadata_readme_is_private_beta_safe() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'readme = "README-PACKAGE.md"' in pyproject
    package_readme = Path("README-PACKAGE.md").read_text(encoding="utf-8")
    assert "PUPIL_TRACKER_PATH" not in package_readme
    assert "app-bundle-pupil-dev" not in package_readme
    assert "make sync-pupil-dev" not in package_readme
    assert "make run-pupil-dev" not in package_readme


def test_private_beta_docs_keep_default_bundle_separate_from_dev_overrides() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/validation/beta-ready-manual-validation.md").read_text(
        encoding="utf-8"
    )
    review = Path("docs/validation/beta-ready-review.md").read_text(encoding="utf-8")

    assert "make app-bundle\nopen dist/Gaze.app" in readme
    assert "PUPIL_TRACKER_PATH is not required for normal private beta use" in readme
    assert "default `dist/Gaze.app`" in checklist
    assert "packaged PupilTracker calibration provider" in checklist
    assert "one calibration child subprocess" in checklist
    assert "dev-bundle/provider guidance" not in checklist
    assert "actionable `make app-bundle-pupil-dev" not in checklist
    assert "Recalibrate now launches the calibration provider" in review


def test_beta_manual_validation_checklist_covers_required_evidence_path() -> None:
    checklist = Path("docs/validation/beta-ready-manual-validation.md").read_text(encoding="utf-8")

    required_phrases = [
        "fake prototype",
        "real trust preview",
        "local `.app`",
        "permissions",
        "hotkeys",
        "calibration",
        "target border",
        "heatmap",
        "Cmd+G activation",
        "disable/panic behavior",
        "failure paths",
        "display layout changes",
        "privacy checks",
        "scalar summary export",
        "Hermes/agent cockpit",
        "Terminal/iTerm",
        "Browser/docs",
        "Discord",
        "AI/chat",
        "Repo editor",
    ]
    lower_checklist = checklist.lower()
    for phrase in required_phrases:
        assert phrase.lower() in lower_checklist

    forbidden_phrases = [
        "record screenshot",
        "save screenshot",
        "window title",
        "document name",
        "raw desktop content",
        "camera frame",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in lower_checklist
