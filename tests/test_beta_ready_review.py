from __future__ import annotations

from pathlib import Path


def test_beta_ready_review_records_gate_4_decision_and_required_evidence() -> None:
    review = Path("docs/validation/beta-ready-review.md").read_text(encoding="utf-8")
    lower_review = review.lower()

    required_phrases = [
        "gaze-045",
        "gate 4",
        "decision",
        "not beta-ready for daily-driver validation until manual evidence passes",
        "automated checks pass",
        "make check",
        "make check-pupil-dev",
        "manual checklist",
        "scalar summary export",
        "known blocking evidence",
        "hermes/agent cockpit",
        "built-in + external display layouts",
        "fake prototype",
        "real trust preview",
        "local `.app`",
        "permissions",
        "hotkeys",
        "calibration",
        "target border",
        "heatmap",
        "cmd+g activation",
        "disable/panic behavior",
        "failure paths",
        "privacy checks",
    ]
    for phrase in required_phrases:
        assert phrase in lower_review


def test_beta_ready_review_keeps_out_of_scope_items_explicit() -> None:
    review = Path("docs/validation/beta-ready-review.md").read_text(encoding="utf-8").lower()

    out_of_scope = [
        "auto-activation",
        "synthetic clicks",
        "launch-at-login",
        "window titles",
        "cross-space switching",
        "signed/notarized distribution",
    ]
    for phrase in out_of_scope:
        assert phrase in review


def test_beta_ready_review_is_content_safe() -> None:
    review = Path("docs/validation/beta-ready-review.md").read_text(encoding="utf-8").lower()

    forbidden_phrases = [
        "record screenshot",
        "save screenshot",
        "camera frame",
        "raw desktop content",
        "window title evidence",
        "document name",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in review
