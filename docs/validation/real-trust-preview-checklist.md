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

- [x] Calibration starts only from explicit Recalibrate/Start calibration action.
- [x] Camera permission is requested only when calibration starts.
- [x] Successful calibration marks Gaze ready and records the current display layout signature.
- [x] Gaze enable does not auto-start camera access.
- [x] Tracking tick consumes scalar gaze samples and does not persist frames.
- [x] Stable gaze locks a visible window target after the stability threshold.
- [x] Border appears around the locked target.
- [x] Border does not intercept mouse clicks.
- [x] Border does not steal key focus.
- [x] Disabling Gaze clears the target and hides the border.

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

- `make check`: ruff passed, ty passed, pytest 110 passed.
- `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker`: ruff passed, ty passed, pytest 110 passed with editable sibling installed under `uv run --no-sync`.
- Runtime wiring tests prove Recalibrate routes through the launched-app menu command path into the real calibration session, and the PupilTracker desktop subprocess is launched only on explicit calibration start.
- Runtime target-selection regression proves the launched PupilTracker demo process PID is excluded from targetable candidates while normal overlapping app windows remain targetable.
- Runtime overlay regression proves the AppKit border panel sets `hidesOnDeactivate=false` and uses a non-activating panel style, so border visibility is not tied to PupilTracker/Python being the foreground app.
- Privacy-safe real provider smoke at 2026-05-16 11:49:23 EDT:
  - `pupil_tracker_available=True`.
  - Editable sibling source path exists.
  - Display provider returned `display_count=1` and scalar signature `2:external:0.0,0.0,5120.0,1440.0@1.0`.
  - Visible-window provider returned `candidate_count=9`; all 9 candidates included owner process IDs.
  - Smoke output contained scalar counts/signature only; no screenshots, frames, window titles, or raw desktop content.

## Manual Validation Notes

Runtime calibration wiring blocker was resolved in this branch before manual validation resumed.

Live calibration status:
- 2026-05-16 16:38:21 EDT: Operator reported PupilTracker validation was good after default timed 9-point calibration. GAZE manual app/display matrix can proceed from this calibrated state.

Resolved blocker:
- Recalibrate now routes through the AppKit menu command path into `RealTrustPreviewController.start_calibration()`.
- Runtime app construction now uses a real `PupilTrackerDesktopCalibrationSession` instead of `FakePrototypeController` fallback behavior.
- The PupilTracker desktop calibration subprocess is launched only when calibration explicitly starts.
- First valid scalar bridged gaze sample after launched calibration promotes Gaze to `READY` and records the current display layout signature.
- 2026-05-16 22:34:02 EDT: Foreground-only targeting root cause was first narrowed away from bridge/calibration: PupilTracker continued producing fresh scalar samples and the demo debug panel continued resolving the gazed app while Gaze's border disappeared off-demo. The launched demo PID is now exposed by the calibration session and excluded from target selection/overlay sync, without excluding unrelated Python apps.
- 2026-05-16 22:56:01 EDT: User clarified calibration and cross-app gaze naming were working; the remaining foreground-only symptom was overlay visibility. The likely AppKit cause is `NSPanel` deactivation behavior: because Gaze and PupilTracker are both Python processes, the border can appear while the Python/PupilTracker app is foreground, then hide when another app becomes active. `AppKitBorderOverlay` now sets `setHidesOnDeactivate_(False)` in addition to `setCanHide_(False)`.
- 2026-05-16 23:05:13 EDT: User reported the border still disappeared off-PupilTracker foreground. The next overlay hypothesis is that the panel must be explicitly non-activating, not just non-hiding. `AppKitBorderOverlay` now includes `NSWindowStyleMaskNonactivatingPanel` in the `NSPanel` style mask while keeping `orderFrontRegardless()`.
- 2026-05-16 23:39:08 EDT: Final manual checkpoint passed on the current same-display runtime path. After calibration and explicit Enable Gaze, Gaze reached ready/locked state, consumed fresh scalar bridge samples, and the target border appeared while a non-PupilTracker app was foreground. Temporary diagnostic menu lines used for this checkpoint were removed before commit.

Current status:
- GAZE-027 current same-display real trust preview path is validated for calibration -> scalar tracking -> target lock -> border overlay while a non-PupilTracker app is foreground.
- Manual launch must provide both `PUPIL_TRACKER_PATH` and `PUPIL_TRACKER_MEDIAPIPE_MODEL`; use `/Users/sage/workspace/sagebynature/pupil-tracker/models/face_landmarker.task` after running `make download-model` in the PupilTracker checkout.
- Broader multi-display/app matrix expansion remains a follow-on hardening pass, not a blocker for leaving Gate 2 fake prototype.
