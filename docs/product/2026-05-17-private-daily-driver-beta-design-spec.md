# Gaze Private Daily-Driver Beta Design Spec

Date: 2026-05-17
Status: Drafted from approved product decisions
Product target: Private daily-driver beta
Primary user: Sage

## Goal

Make Gaze feel like a calm, polished, trustworthy macOS utility that Sage can use daily for gaze-assisted app activation, with manual Cmd+G as the default path and opt-in auto-activate available behind clear controls.

This target is not an invite-only beta or public v1. It does not require signed/notarized distribution, updater infrastructure, public support flows, or broad hardware coverage. It does require the product to stop feeling like a prototype on Sage's Mac.

## Approved Decisions

1. Product target: private daily-driver beta.
2. Primary UX surface: menu bar plus polished setup/settings window.
3. Visual direction: calm premium utility.
4. Calibration provider strategy: Gaze-owned calibration UI; PupilTracker remains the tracking/model engine.
5. Calibration UX style: guided wizard.
6. Action plan structure: execution-ready phase plan first; detailed TDD tranche plan after approval.
7. First phase priority: Gaze-owned calibration foundation.
8. Heatmap scope: remove from user-facing private beta UI; keep internal/developer only if useful.
9. Target preview privacy: app name only.
10. Settings scope: essentials plus approved automation controls.
11. Diagnostics posture: quiet user-facing scalar export.
12. Automation scope update: include auto-activate on/off and debounce configuration in the private beta scope, off by default.
13. Plan artifacts: separate design spec and action plan.

## Product Posture

Gaze is a trust-first desktop control utility. It should feel like a native Mac utility with premium restraint: quiet, legible, precise, and hard to misuse.

The app should answer four questions quickly:

1. Is Gaze on?
2. Is calibration ready?
3. What app does Gaze think I am looking at?
4. How do I stop or recover immediately?

The app must not look or behave like a debugging dashboard during normal use.

## Non-Negotiables

- Manual activation remains the default path.
- Auto-activation is allowed only as an explicit opt-in setting, off by default, with clear status and an immediate off switch.
- Auto-activation must use the same owning-app activation path as Cmd+G and must respect lock/debounce/cooldown safeguards.
- No synthetic clicks.
- No launch-at-login requirement.
- No user-facing heatmap control.
- No window titles, document names, URLs, filenames, screenshots, camera frames, or raw desktop content in UI, diagnostics, logs, or validation evidence.
- App names are allowed in UI because they are the trust signal.
- Disable behaves like a panic stop: hide overlays, block activation, clear/neutralize target state.
- Camera permission is requested just in time, during calibration.

## UX Architecture

### Daily Surface: Menu Bar

The menu bar dropdown is the daily cockpit. It should be compact, native-feeling, and clear.

Required daily controls:

- Gaze on/off.
- Current calibration state: not ready, calibrating, ready, degraded, retry required.
- Current target app name or no target.
- Lock/activation readiness.
- Manual activation hint: Cmd+G.
- Auto-activate mode indicator when enabled.
- Recalibrate.
- Settings.
- Quit.

User-facing menu should not include:

- Heatmap toggle.
- Per-app policy.
- Developer tuning knobs.

### Trust Surface: Setup/Settings Window

The setup/settings window is where polish matters most. It should carry onboarding, calibration, hotkeys, privacy, diagnostics, and reset actions.

Required sections:

1. Status overview
   - Gaze enabled/disabled.
   - Calibration state.
   - Current target readiness.
   - Display layout state.

2. Guided calibration
   - Start/recalibrate.
   - Camera/privacy explanation.
   - Readiness checks.
   - Target sequence.
   - Result quality.
   - Clear retry guidance.

3. Controls
   - Gaze on/off.
   - Target border on/off.
   - Hotkey display/editing.
   - Auto-activate on/off, clearly off by default.
   - Auto-activate debounce duration, bounded to safe values.
   - Clear copy that Cmd+G remains available and disable stops all activation.

4. Privacy
   - Plain explanation of what stays local.
   - Explicit list of excluded data: no screenshots, frames, window titles, URLs, filenames, document names, or raw desktop content.

5. Diagnostics
   - Quiet export action for scalar summary only.
   - Short explanation of included fields: state enums, counts, timestamps, confidence/lock metrics, display-layout status.

6. Reset
   - Reset local calibration profile.

### Developer Surface

Developer diagnostics may exist separately, but they must not pollute the daily UI.

Allowed developer-only controls:

- Heatmap or gaze trail diagnostics.
- Fake gaze/window/debug controls.
- Raw scalar bridge state inspection.
- Internal calibration provider diagnostics.

Developer UI must remain gated by development profile, debug menu, or explicit launch/runtime flag.

## Gaze-Owned Calibration Experience

The current source-tree `desktop_demo` path is not acceptable as the final private daily-driver UX. Gaze should own the visible calibration flow.

PupilTracker remains responsible for gaze/tracking/model internals. Gaze owns:

- Window layout.
- Copy and trust messaging.
- Permission timing.
- Calibration target sequence presentation.
- Progress and failure states.
- Lifecycle integration with Gaze readiness and persisted calibration.

### Wizard Flow

Step 1: Privacy and permission

- Explain why camera is needed.
- Explain that processing is local.
- Explain what is never recorded or exported.
- Camera permission is requested only after the user starts calibration.

Step 2: Camera and posture readiness

- Show calm readiness checks, not a technical dashboard.
- Validate face/camera availability through scalar or ephemeral local state.
- Provide actionable guidance for lighting, posture, distance, and display layout.

Step 3: Calibration target sequence

- Full-window or focused calibration surface using Gaze-owned visuals.
- Targets should feel precise and calm.
- Progress should be obvious.
- Failure should be recoverable.

Step 4: Quality result

- Ready: enable normal targeting.
- Degraded: usable, but recommend recalibration.
- Retry required: explain why and provide next action.
- Persist last-good scalar calibration profile when valid.

## Visual Direction

Style: calm premium utility.

Design qualities:

- Native Mac structure.
- Soft neutral background.
- High legibility.
- Precise spacing.
- Minimal visual noise.
- One restrained accent color for ready/locked state.
- Clear but non-alarming degraded/retry states.
- Subtle target border/glow that builds trust without covering content.

Avoid:

- Futuristic eye-tech gimmicks.
- Heavy dashboards.
- Neon telemetry aesthetic.
- Emoji icons.
- Visible dead controls.
- Dense developer language in product UI.

## Privacy Contract

Allowed user-facing target detail:

- App name only, such as Browser, Terminal, Discord, Editor, or No target.

Disallowed everywhere in private beta outputs:

- Window titles.
- Document names.
- URLs.
- Filenames.
- Screenshots.
- Camera frames.
- Raw desktop content.
- Raw visual/video payloads.

Scalar diagnostics may include:

- Calibration state.
- Gaze enabled state.
- Confidence/lock metrics.
- Activation success/failure counts.
- Auto-activation enabled state.
- Auto-activation debounce value.
- Auto-activation trigger/suppression counts.
- No-target counts.
- Already-frontmost counts.
- Display-layout state.
- Hotkey registration status.
- Timestamps or durations.

## Acceptance Criteria

The private daily-driver beta design is accepted when:

1. Gaze starts as a polished menu-bar utility, not a dashboard.
2. The setup/settings window is visually calm and product-grade.
3. Calibration is Gaze-owned at the UI layer and no longer exposes PupilTracker's demo UI as the product path.
4. Recalibration from the default app path works without `PUPIL_TRACKER_PATH` as a user-facing requirement.
5. Heatmap is absent from user-facing beta UI.
6. Target preview shows app name only.
7. Settings contains essentials plus the approved automation controls: auto-activate on/off and bounded debounce configuration.
8. Scalar export is present but quiet.
9. Disable blocks activation, hides overlays, and clears or neutralizes current target/lock/preview state.
10. Developer diagnostics are absent from the default private beta UI and require an explicit development/debug/profile gate.
11. Runtime validation proves auto-activation is off by default, only runs after explicit opt-in, respects target lock/debounce/cooldown safeguards, and uses no synthetic-click path.
12. Automated gates and manual private beta validation pass with scalar-only evidence.
13. Privacy guard tests and checklist coverage explicitly block the full forbidden-data set: screenshots, camera frames, raw visual/video payloads, window titles, document names, URLs, filenames, and raw desktop content across UI, logs, diagnostics/export, tests, docs, and validation evidence.

## Explicitly Out of Scope

- Invite-only beta packaging polish.
- Public v1 onboarding/support flows.
- Signed/notarized distribution.
- Updater infrastructure.
- Synthetic clicks.
- User-facing heatmap.
- Window title display.
- Cross-Space activation promises.
- Exact individual window raising beyond owning-app activation.
