# Gaze Beta-Ready Manual Validation Checklist

Slice: GAZE-044
Scope: define the beta-ready evidence path for Sage's daily-driver validation.

Use this checklist with scalar notes only. Record pass/fail, app category, display layout label, calibration state, activation outcome, counts, and short generic notes. Do not record visual captures, content-bearing labels, URLs, file labels, or desktop details.

## Automated Gate

- [ ] `make check` passes.
- [ ] `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker` passes.
- [ ] Local unsigned bundle builds with `make app-bundle`.
- [ ] Bundle contains `dist/Gaze.app/Contents/Resources/models/face_landmarker.task`.
- [ ] Default bundle uses PyPI/release `pupil-tracker`; editable sibling mode is not used unless explicitly testing dev mode.
- [ ] Scalar summary export is attached as JSON text or copied into validation notes.

## Validation Scope

- [ ] fake prototype baseline remains safe.
- [ ] real trust preview path works after explicit calibration.
- [ ] local `.app` launches outside the source tree.
- [ ] permissions are requested just in time.
- [ ] hotkeys work with default and edited bindings.
- [ ] calibration can complete, degrade, and retry without launch-time camera access.
- [ ] target border appears only after target lock.
- [ ] heatmap is optional, off by default, session-local, and clearable.
- [ ] Cmd+G activation uses owning-app activation only.
- [ ] disable/panic behavior clears target, hides overlays, and blocks activation.
- [ ] failure paths produce subtle non-modal feedback.
- [ ] display layout changes degrade calibration and recommend recalibration.
- [ ] privacy checks pass before beta-ready review.

## Permissions and Local App Lifecycle

- [ ] Launch from `dist/Gaze.app` with the repo not as the active working directory.
- [ ] Menu-bar app appears without opening a persistent dashboard.
- [ ] Camera permission appears only after explicit Recalibrate/calibration start.
- [ ] Recalibrate does not implicitly enable Gaze tracking.
- [ ] Accessibility or automation prompts are not required for MVP activation behavior.
- [ ] Missing model/dependency guidance is actionable.

## Hotkeys

- [ ] Cmd+G activation works when a target is locked.
- [ ] Option+Cmd+G toggles Gaze on/off.
- [ ] Disabled hotkeys do not invoke actions.
- [ ] Rebound hotkeys invoke the selected action.
- [ ] Conflict or unavailable registration feedback is visible without a modal interruption.

## Real Trust Preview Flow

- [ ] Start with Gaze disabled.
- [ ] Run calibration explicitly.
- [ ] Enable Gaze explicitly after calibration.
- [ ] Verify scalar tracking readiness in the menu/status surface.
- [ ] Hold gaze over a visible app until the target border locks.
- [ ] Use Cmd+G activation.
- [ ] Confirm already-frontmost activation reports a no-op status.
- [ ] Confirm unavailable activation reports a generic failure status.
- [ ] Disable Gaze and confirm no activation occurs.

## App Coverage Matrix

Record only pass/fail, category, display layout label, activation outcome, and scalar notes.

| Category | Built-in only | Built-in + external layout A | Built-in + external layout B | Notes |
| --- | --- | --- | --- | --- |
| Hermes/agent cockpit | [ ] | [ ] | [ ] | |
| Terminal/iTerm | [ ] | [ ] | [ ] | |
| Browser/docs | [ ] | [ ] | [ ] | |
| Discord | [ ] | [ ] | [ ] | |
| AI/chat | [ ] | [ ] | [ ] | |
| Repo editor | [ ] | [ ] | [ ] | |

## Display Layout Changes

- [ ] Built-in-only layout calibrates and targets.
- [ ] Built-in + external layout A calibrates and targets.
- [ ] Built-in + external layout B calibrates and targets.
- [ ] Changing layouts marks calibration degraded.
- [ ] Recalibration after layout change records a new scalar display signature.

## Failure Paths

- [ ] No target under gaze leaves activation blocked.
- [ ] Low-confidence or stale gaze sample degrades readiness without crashing.
- [ ] Missing owner process identity reports unavailable.
- [ ] macOS activation refusal reports unavailable.
- [ ] Hotkey conflict reports registration issues without binding text in scalar diagnostics.

## Privacy Checks

- [ ] No visual captures are saved.
- [ ] No tracker image data is saved.
- [ ] No content-bearing labels are shown in beta evidence.
- [ ] No desktop details are logged or exported.
- [ ] Validation notes remain scalar and generic.
- [ ] Scalar summary export contains only `gaze.scalar-summary.v1` fields and scalar values.

## Manual Validation Session Notes

Session status: partial pass with beta blockers.

Passed in dev-mode local bundle:

- [x] local `.app` launched from `dist/Gaze.app`.
- [x] menu-bar app appeared without a persistent dashboard requirement.
- [x] safe default state: Gaze started disabled.
- [x] disabled activation produced no focus change.
- [x] settings/setup surface matched the trust-first posture.
- [x] editable sibling dev-mode bundle launched calibration after explicit Recalibrate.
- [x] camera/tracking started only after explicit Recalibrate.
- [x] no Accessibility prompt appeared during the tested flow.
- [x] explicit Enable Gaze began consuming live scalar samples.
- [x] target border appeared only after a locked target.
- [x] border remained non-interactive during validation.
- [x] menu Activate Target brought the owning app forward after the AppKit lookup fix.
- [x] already-frontmost activation was a no-op.
- [x] no-target activation did not bring an app forward.
- [x] Disable Gaze hid/cleared targeting and blocked activation.
- [x] privacy posture passed visible UI inspection: no content labels, location strings, visual captures, tracker imagery, desktop payloads, or raw feature vectors were shown in Gaze surfaces.
- [x] app and calibration subprocesses quit cleanly at the end of the run.

Known blockers before beta-ready promotion:

- [ ] Default release/PyPI bundle Recalibrate produced no actionable visible result when the desktop calibration source was unavailable.
- [ ] Cmd+G did not work as a true global hotkey while another app was frontmost.
- [ ] Toggle Heatmap produced no visible effect because the runtime does not wire a real heatmap overlay.
- [ ] Built-in/external display-layout degradation was skipped and remains pending manual evidence.
- [ ] Scalar summary export from the live validation run remains pending.

Fix applied during validation:

- [x] AppKit activation lookup now uses the singular process-identifier API; regression coverage added.

## Scalar Summary Export

Use the `export_scalar_summary_json()` helper with the active diagnostics snapshot. The export may include:

- `enabled`
- `calibration_state`
- `last_confidence`
- `target_locked`
- `lock_duration_ms`
- `last_activation_result`
- `already_frontmost_count`
- `no_target_count`
- `display_layout_degraded_events`
- `hotkey_registration_status`
- `hotkey_registration_issue_count`

The export must reject non-scalar values and content-like fields before the beta-ready review.
