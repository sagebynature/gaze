# Gaze PRD and MVP Scope

Date: 2026-05-15
Status: Draft for execution planning
Product: Gaze
Platform: macOS native desktop application
Primary dependency: PupilTracker (`../pupil-tracker`, PyPI package `pupil-tracker`)
Native integration: PyObjC/AppKit/CoreGraphics where possible

## 1. Product Summary

Gaze is a macOS native utility that lets a user bring an application window into focus by looking at it. The product starts from a trust-first workflow: calibrate once, show what window Gaze thinks the user is looking at, then let the user press a hotkey to activate that window.

Automatic activation is intentionally not the primary MVP path. It remains a later, opt-in advanced mode because false positives in desktop focus are disruptive.

## 2. Problem

Window switching is frequent and interruptive on multi-window macOS workflows. Keyboard shortcuts, Mission Control, mouse clicks, and trackpad gestures all require the user to shift physical action away from the thing they are already looking at.

Gaze should make attention a safe targeting signal without taking control too early.

## 3. Target Users

### Primary

- Developers, researchers, operators, and power users who work across many windows.
- Users with multi-monitor or large-screen setups.
- Users who want lower-friction window switching but still want final control.

### Secondary

- Presenters who need to bring notes, slides, demos, or references forward quickly.
- Accessibility users who benefit from reducing mouse/trackpad dependence.
- Users exploring gaze-assisted desktop control.

## 4. Product Principles

1. Trust before automation.
2. Manual activation before auto activation.
3. Clear state at all times: off, calibrating, ready, degraded, unavailable.
4. No synthetic clicks in the MVP.
5. Privacy-first diagnostics: no camera frames, screenshots, or raw desktop content stored by default.
6. Native macOS feel: menu bar control, system permissions, global hotkeys, subtle overlays.
7. Fast escape path: users can disable Gaze immediately.

## 5. MVP Goal

A user can install Gaze, calibrate with the webcam, look at a visible app window, see a subtle target confirmation, and press Cmd+G to bring that app forward.

## 6. MVP User Journey

1. User launches Gaze.
2. Gaze shows onboarding and asks for required permissions only when needed:
   - Camera permission for pupil tracking.
   - Accessibility permission only if a later activation path requires it; the first slice should prefer AppKit activation and avoid unnecessary permission asks.
3. User starts calibration.
4. Gaze runs a guided calibration flow using PupilTracker.
5. Gaze shows calibration quality and a clear recommendation:
   - Ready
   - Usable but recalibration recommended
   - Retry required
6. User enables Gaze from the app or menu bar.
7. User looks at a visible window.
8. Gaze draws a subtle border around the candidate window.
9. User presses Cmd+G.
10. Gaze activates the owning application for the candidate window.
11. User can disable Gaze instantly with the toggle or hotkey.

## 7. MVP Scope

### In Scope

#### Calibration

- Guided first-run calibration.
- Recalibration action available from the main window and menu bar.
- Calibration quality status.
- Clear failure guidance: lighting, camera position, posture, and retry.
- Persisted calibration profile for the current Mac/user session where feasible.

#### Gaze Targeting

- Use PupilTracker to produce screen-space gaze samples.
- Use CoreGraphics visible-window enumeration to identify candidate windows.
- Select the topmost visible window containing the current gaze point.
- Smooth noisy gaze samples before selecting a target.
- Expose confidence and degraded-state messaging in the UI.

#### Manual Activation

- Default activation hotkey: Cmd+G.
- Activation brings the owning app/window candidate forward without synthetic clicks.
- Repeated activation is suppressed while the gaze target remains unchanged.
- Activation failures are shown as recoverable statuses, not crashes.

#### Gaze State Toggle

- User can turn Gaze on/off from the app.
- User can bind a hotkey to turn Gaze on/off.
- Gaze starts in a safe non-activating state until the user enables it.

#### Target Border Overlay

- Toggle: show/hide target border.
- Default: on during MVP because it builds trust.
- Visual style: subtle, identifiable, low-distraction.
- Border should not intercept mouse/keyboard events.
- Border should avoid covering content-heavy edges where possible.

#### Heatmap Overlay

- Toggle: show/hide gaze heatmap.
- Default: off.
- Intended for calibration/debugging, not always-on use.
- Clear heatmap action.
- Use decayed or session-local data only unless the user explicitly exports diagnostics.

#### Settings

- Manual activation hotkey.
- Gaze on/off hotkey.
- Target border toggle.
- Heatmap toggle.
- Optional auto-activate setting stub, disabled by default and clearly marked advanced/later.
- Debounce duration field may exist in settings but is only active when auto-activate is enabled in a later release.

#### Privacy and Safety

- No camera video recording by default.
- No screenshots stored by default.
- No raw window title telemetry by default unless explicitly enabled for diagnostics.
- Clear explanation of what stays local.
- Explicit opt-in for any logging/export.

### Out of Scope for MVP

- Auto-activate as the default experience.
- Synthetic mouse clicks.
- Full window raising/reordering beyond app activation unless needed and explicitly reviewed.
- Cross-platform support.
- Multi-user profile sync.
- Cloud telemetry.
- Advanced dwell gestures.
- Eye-controlled cursor movement.
- App Store packaging until the native app and permission model are stable.

## 8. Post-MVP / V1.1 Candidates

### Auto-Activate Mode

- Disabled by default.
- Requires explicit opt-in.
- Configurable debounce/dwell time before activation.
- Cooldown to prevent focus thrashing.
- Confidence threshold before activation.
- Per-app allow/deny list.
- Panic hotkey to immediately disable all automation.

### Advanced Window Targeting

- Better handling for overlapping windows.
- Multiple displays.
- Spaces and fullscreen apps.
- Window-specific activation if AppKit app activation is too coarse.
- Exclude system overlays, menu bar, desktop, and transient windows.

### Accessibility Use Cases

- Larger calibration targets.
- Reduced-motion mode.
- Dwell-to-confirm activation.
- Voice confirmation pairing.
- Assisted mode where gaze selects and a switch/hotkey confirms.

### Pro Workflow Use Cases

- Presenter mode: gaze selects notes, slides, browser, or terminal during a presentation.
- Coding mode: quick focus between editor, terminal, browser, and docs.
- Research mode: focus follows attention across notes, PDFs, browser, and writing app.
- Monitoring mode: bring dashboards/log windows forward without mouse movement.

## 9. Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-001 | Launch a native macOS app shell | MVP | PyObjC/AppKit preferred |
| FR-002 | Run guided calibration through PupilTracker | MVP | Camera permission required |
| FR-003 | Persist usable calibration state | MVP | Local only |
| FR-004 | Enumerate visible macOS windows | MVP | CoreGraphics |
| FR-005 | Map gaze point to window candidate | MVP | Topmost visible match |
| FR-006 | Draw non-interactive target border | MVP | Subtle and identifiable |
| FR-007 | Register manual activation hotkey | MVP | Default Cmd+G |
| FR-008 | Activate candidate owning app | MVP | AppKit; no synthetic clicks |
| FR-009 | Toggle Gaze on/off | MVP | UI plus hotkey binding |
| FR-010 | Toggle heatmap | MVP | Off by default |
| FR-011 | Clear heatmap | MVP | Session-local |
| FR-012 | Show calibration/gaze confidence status | MVP | Builds trust |
| FR-013 | Suppress repeated activation | MVP | Avoid focus churn |
| FR-014 | Configurable auto-activate debounce | Later | Only when auto-activate ships |
| FR-015 | Auto-activate mode | Later | Disabled by default |
| FR-016 | Per-app allow/deny list | Later | Important for automation safety |
| FR-017 | Panic hotkey | Later but high value | Consider pulling into MVP if cheap |

## 10. Non-Functional Requirements

### Performance

- UI remains responsive during camera/tracking.
- Border overlay updates smoothly enough to feel live without flicker.
- Activation hotkey response feels immediate after target lock.

### Reliability

- Camera startup failure produces actionable guidance.
- Missing PupilTracker dependency produces setup guidance.
- Activation failure does not crash the app.
- Gaze disabled means no activation side effects.

### Privacy

- All gaze processing runs locally.
- Diagnostics are opt-in.
- No frames, screenshots, or raw desktop content are persisted by default.

### Testability

- Gaze target selection is pure and testable.
- Window activation is behind an injectable seam.
- Hotkey handling is separable from activation business logic.
- Overlay rendering has a fakeable window/candidate source.

## 11. UX Requirements

### Main Window

The first window should be calm and explicit. It should have these areas:

1. Status header:
   - Gaze off/on
   - Calibration ready/degraded/not ready
   - Camera status
2. Primary action:
   - Calibrate / Recalibrate
3. Target preview:
   - Current candidate app/window label if privacy setting allows display
   - Confidence indicator
   - Manual activation hint: Look at a window, press Cmd+G
4. Controls:
   - Enable Gaze
   - Show target border
   - Show heatmap
   - Settings
5. Safety note:
   - Manual activation only in MVP
   - No clicks are synthesized

### Overlay

- Border opacity should be low enough not to dominate content.
- Use a thin rounded rectangle or soft glow.
- Use one accent color consistently.
- Avoid rapid changes by requiring a short target stability window.
- Heatmap should use a transparent gradient and be easy to clear.

### Menu Bar

- Gaze on/off
- Calibrate/Recalibrate
- Current status
- Settings
- Quit

## 12. Success Metrics

### MVP Validation Metrics

- User can complete calibration without developer intervention.
- User can identify which window Gaze is targeting before activating.
- Cmd+G activates the intended app in common workflows.
- False target rate is low enough that the border feels trustworthy.
- Gaze can be disabled quickly and reliably.

### Quantitative Signals

- Calibration completion rate.
- Calibration retry rate.
- Manual activation success rate.
- Manual activation wrong-target rate from local test logs.
- Average time from gaze target lock to activation.
- Crash-free session rate.

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Gaze accuracy is inconsistent | High | Manual activation first, confidence status, recalibration guidance |
| Auto-focus annoys users | High | Defer auto-activation; explicit opt-in only |
| Hotkey conflicts with apps | Medium | User-editable hotkeys; conflict detection if feasible |
| macOS activation limitations | Medium | Prefer AppKit first; report unavailable cleanly |
| Permission prompts scare users | Medium | Explain why each permission is needed, ask only when needed |
| Overlay distracts users | Medium | Subtle default style and toggle |
| Window titles are private | Medium | Avoid persistent raw title telemetry by default |

## 14. Recommended First Release Cut

The first release should be called a trust preview, not full automation.

Build order:

1. Native app shell and permission-aware onboarding.
2. PupilTracker integration and calibration status.
3. Window candidate model and target selection.
4. Border overlay for current target.
5. Manual Cmd+G activation.
6. Heatmap/debug view.
7. Settings and hotkey customization.
8. Polish, packaging, manual validation.

## 15. Open Product Decisions

1. Should the Gaze on/off default hotkey be Cmd+Shift+G, Option+Cmd+G, or user-defined only?
2. Should the MVP show app/window names in the UI by default, or hide them behind a privacy setting?
3. Should panic disable be part of MVP even though auto-activate is deferred?
4. Should calibration profile persistence be per-display setup or just last-used screen geometry for MVP?
5. Should Gaze ship as menu-bar-first, window-first, or hybrid? Recommendation: hybrid, with menu bar always available and a focused setup window.
