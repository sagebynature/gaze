# Gaze Real Trust Preview Validation Checklist

Date: 2026-05-16 11:49:23 EDT
Operator: Sage
Commit: feature/real-trust-preview-validation pre-commit
Slice: GAZE-027

## Automated Gate

- [x] `make check` passes.
- [x] `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker` passes when using the editable sibling tracker.
- [x] Real display provider returns scalar display geometry only.
- [x] Real visible-window provider returns scalar candidate geometry and owner process IDs only.

## Real Trust Preview Runtime

- [ ] Calibration starts only from explicit Recalibrate/Start calibration action.
- [ ] Camera permission is requested only when calibration starts.
- [ ] Successful calibration marks Gaze ready and records the current display layout signature.
- [ ] Gaze enable does not auto-start camera access.
- [ ] Tracking tick consumes scalar gaze samples and does not persist frames.
- [ ] Stable gaze locks a visible window target after the stability threshold.
- [ ] Border appears around the locked target.
- [ ] Border does not intercept mouse clicks.
- [ ] Border does not steal key focus.
- [ ] Disabling Gaze clears the target and hides the border.

## App Coverage Matrix

Run each case with Cmd+G manual activation after target lock.
Do not record screenshots, camera frames, window titles, or raw desktop content.
Record only pass/fail, app category, display layout label, activation outcome, and notes.

| Category | Built-in only | Built-in + external layout A | Built-in + external layout B | Notes |
| --- | --- | --- | --- | --- |
| Terminal/iTerm | [ ] | [ ] | [ ] | |
| Browser/docs | [ ] | [ ] | [ ] | |
| Discord | [ ] | [ ] | [ ] | |
| AI/chat app | [ ] | [ ] | [ ] | |
| Repo editor | [ ] | [ ] | [ ] | |

## Activation Behavior

- [ ] Locked target with owner process ID activates through AppKit owning-app activation.
- [ ] Already-frontmost target reports "Already frontmost" and does not repeatedly activate.
- [ ] Missing/refused activation reports unavailable without modal disruption.
- [ ] Activation never performs synthetic mouse clicks.

## Display Layout Behavior

- [ ] Built-in-only calibration and targeting works.
- [ ] Built-in + external layout A calibration and targeting works.
- [ ] Built-in + external layout B calibration and targeting works.
- [ ] Layout change marks calibration degraded and recommends recalibration.
- [ ] Recalibration after layout change records a new scalar display signature.

## Privacy Gate

- [ ] No screenshots are saved.
- [ ] No camera frames are saved.
- [ ] No window titles are shown in UI or logs.
- [ ] No raw desktop content is logged or exported.
- [ ] Validation notes contain scalar status only.

## Current Automated Evidence

- `make check`: ruff passed, ty passed, pytest 105 passed.
- `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker`: ruff passed, ty passed, pytest 105 passed with editable sibling installed under `uv run --no-sync`.
- Runtime wiring tests prove Recalibrate routes through the launched-app menu command path into the real calibration session, and the PupilTracker desktop subprocess is launched only on explicit calibration start.
- Privacy-safe real provider smoke at 2026-05-16 11:49:23 EDT:
  - `pupil_tracker_available=True`.
  - Editable sibling source path exists.
  - Display provider returned `display_count=1` and scalar signature `2:external:0.0,0.0,5120.0,1440.0@1.0`.
  - Visible-window provider returned `candidate_count=9`; all 9 candidates included owner process IDs.
  - Smoke output contained scalar counts/signature only; no screenshots, frames, window titles, or raw desktop content.

## Manual Validation Notes

Runtime calibration wiring blocker was resolved in this branch before manual validation resumed.

Resolved blocker:
- Recalibrate now routes through the AppKit menu command path into `RealTrustPreviewController.start_calibration()`.
- Runtime app construction now uses a real `PupilTrackerDesktopCalibrationSession` instead of `FakePrototypeController` fallback behavior.
- The PupilTracker desktop calibration subprocess is launched only when calibration explicitly starts.
- First valid scalar bridged gaze sample after launched calibration promotes Gaze to `READY` and records the current display layout signature.

Current status:
- Automated runtime wiring coverage is in place.
- Manual launch must provide both `PUPIL_TRACKER_PATH` and `PUPIL_TRACKER_MEDIAPIPE_MODEL`; use `/Users/sage/workspace/sagebynature/pupil-tracker/models/face_landmarker.task` after running `make download-model` in the PupilTracker checkout.
- Manual validation remains required for the app coverage matrix and built-in + external display layouts before GAZE-027 can be closed.
