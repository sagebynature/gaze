# Gaze Menu-Bar Beta Design

Date: 2026-05-15
Status: Approved design direction; written for review
Product: Gaze
Platform: macOS native desktop utility
Primary user: Sage
Primary workflow: Hermes/agent-heavy coding cockpit

## Goal

Gaze is a menu-bar-first macOS utility that helps Sage switch focus across a coding cockpit by looking at a visible app window and pressing Cmd+G.

The MVP target is beta-ready for Sage, not public beta. It must be safe enough and polished enough for daily-driver validation on Sage's Mac, with a clear path from fake prototype to real trust preview to beta-ready MVP.

## Product Posture

Gaze is a trust-first desktop control utility.

Trust rules:

- Manual activation only in MVP.
- No auto-activation in MVP.
- No synthetic clicks.
- No launch-at-login in MVP.
- No cross-Space switching in MVP.
- No public/general beta onboarding in MVP.
- Disable behaves like a panic stop: clear target, hide overlays, and block activation.
- No dedicated panic hotkey in MVP; the Disable action and Option+Cmd+G toggle provide the panic-stop behavior.
- If the target border is locked, Cmd+G may activate.
- If no target is locked, Cmd+G reports no target or not ready.

The product should feel like a calm background utility, not a dashboard.

## Primary Workflow

Optimize first for Sage's coding cockpit:

- Terminal or iTerm.
- Browser.
- Discord.
- AI/chat apps.
- Repo editor.

The important switching pattern is broad: editor, terminal, browser/docs, and AI/chat are all first-class. The validation matrix should reflect the whole Hermes/agent cockpit rather than one app pair.

## App Shell

### Daily Surface: Menu Bar

Gaze is menu-bar-first. The menu bar item is the always-available control point.

The menu bar icon uses state variants:

- Off.
- Calibrating.
- Ready.
- Degraded.

The icon should not normally include permanent text. Target details belong in the dropdown/popover so the utility does not consume menu bar space.

### Menu Dropdown / Popover

The MVP dropdown should include trust controls:

- Gaze on/off.
- Calibration status.
- Current target app name only, such as Safari, Terminal, Discord, or No target.
- Confidence/lock state.
- Border toggle.
- Heatmap toggle.
- Recalibrate.
- Settings.
- Quit.

The menu should answer four questions quickly:

1. Is Gaze on?
2. Is calibration ready?
3. What does Gaze think I am looking at?
4. Can I stop it immediately?

### Setup and Settings Window

A dedicated app window is not the daily surface. Use a lightweight setup/settings window only for flows that need space:

- First-run onboarding.
- Permission explanation.
- Calibration and recalibration.
- Hotkey editing.
- Border/heatmap settings.
- Privacy/name display settings.
- Diagnostics profile settings.

Settings scope for MVP is essentials only. Do not show disabled auto-activation, debounce, or per-app policy controls in product UI. Mention future automation only in documentation.

### Developer Panel

The fake prototype needs a separate Developer panel, opened from the menu bar in development builds.

The Developer panel is not part of the end-user setup/settings window. It should provide fake controls without contaminating the product surface.

Developer panel capabilities:

- Start/stop scripted fake target sequence.
- Manually select fake target app.
- Set fake target confidence/lock state.
- Set fake frontmost app state.
- Trigger fake activation success.
- Trigger fake activation failure.
- Trigger no-target and degraded states.

## Milestones

### Milestone 1: Fake Prototype

Purpose: prove the end-to-end trust loop without camera, real window enumeration, or real app activation.

Build:

- Menu bar utility shell.
- Setup/settings shell.
- Separate Developer panel.
- Fake gaze source.
- Fake window candidates.
- Fake frontmost app state.
- Scripted fake target sequence.
- Manual fake target/debug controls.
- Real non-interactive border overlay around fake candidate bounds.
- Cmd+G activation command behind an activation seam.
- Fake activation outcomes.
- Success flash/toast.
- Activation failure toast plus menu/status update.
- Already-frontmost no-op status.

Acceptance:

- Importing modules causes no camera, window enumeration, hotkey, overlay, or activation side effects.
- Gaze starts off.
- Disable clears target, hides overlays, and blocks activation.
- Real overlay does not intercept input, verified by style contract plus manual validation.
- If fake target is locked and not frontmost, Cmd+G calls fake activation once.
- If fake target is already frontmost, Cmd+G reports Already frontmost and does not activate repeatedly.
- If no target is locked, Cmd+G reports no target/not ready.

### Milestone 2: Real Trust Preview

Purpose: replace fake sources with real calibration, gaze samples, visible-window targeting, and owning-app activation while keeping the trust-first UX.

Build:

- Editable sibling `../pupil-tracker` development mode.
- PyPI dependency path preserved for release.
- Real PupilTracker calibration adapter.
- Real gaze sample stream.
- Real visible-window candidate provider.
- Current Space visible-window targeting.
- Built-in + one external display support.
- Display geometry/signature detection.
- Degraded calibration on display layout change.
- AppKit owning-app activation only.

Acceptance:

- Camera permission is requested just-in-time when calibration starts.
- Accessibility permission is not requested unless a future native activation path requires it.
- Calibration can produce ready, degraded, or retry-required state.
- Display layout changes mark calibration degraded and recommend recalibration.
- Current Space visible windows can be targeted; other Spaces are ignored.
- Desktop, menu bar, Dock, and system UI produce no target.
- Targeting works across built-in + one external display in at least two layouts.
- Activation brings the owning app forward without synthetic clicks.

### Milestone 3: Beta-Ready for Sage

Purpose: make Gaze credible for Sage's daily validation.

Build:

- Local `.app` bundle after the fake prototype is proven.
- Editable hotkeys with conflict/unavailable feedback.
- Cmd+G manual activation.
- Option+Cmd+G Gaze on/off toggle.
- Border/glow polish.
- Optional heatmap, off by default, session-local, clearable.
- Dev scalar diagnostics on by default.
- Release/default profile scalar diagnostics off by default.
- Manual validation checklist.
- Scalar session summary export.

Acceptance:

- Local `.app` launches outside the source tree.
- Hotkey registration failures are surfaced and can be reconfigured.
- The menu bar icon and menu remain usable through off, calibrating, ready, and degraded states.
- Validation covers Terminal/iTerm, browser, Discord, AI/chat apps, and repo editor.
- Validation covers variable built-in + external display layouts.
- Validation evidence contains scalar diagnostics only, no content.

## Targeting Rules

### Candidate Scope

MVP targets visible application windows in the current Space only.

Do not target:

- Desktop.
- Menu bar.
- Dock.
- System UI.
- Windows in other Spaces.
- Non-visible or hidden windows.

When gaze lands on non-window UI, Gaze should report no target and hide the border. Anti-flicker should be handled through stability timing, not by pretending system UI is a target.

### Stability Timing

Use balanced target stability timing as the initial policy:

- Border lock after roughly 300-500 ms of stable gaze.
- Border lock and manual activation threshold are the same.

This keeps the mental model simple:

- Border shown/locked means Cmd+G can activate.
- No border/lock means Cmd+G will not activate.

Thresholds may become configurable constants after scalar diagnostics show real behavior.

### Degraded Calibration

Degraded calibration remains useful.

- Preview is allowed.
- Manual activation is allowed when a target is locked.
- UI should clearly say degraded and recommend recalibration.

If implementation needs stricter internal confidence under degraded calibration, it must not create a confusing state where the user sees a locked border but Cmd+G is blocked. The user-facing rule remains: locked border means activation is allowed.

### Calibration Profile Persistence

MVP uses a last-good calibration profile.

- If no last-good profile exists, calibration is required before live targeting can be trusted.
- The last-good profile is associated with a display geometry/signature.
- When the display layout changes, Gaze keeps the profile but marks calibration degraded and recommends recalibration.
- A degraded last-good profile may still preview and manually activate when a target is locked.
- A retry-required calibration state blocks trust until calibration succeeds again.

## Activation Rules

### MVP Activation

MVP activates the owning app only through AppKit/process activation.

It does not promise exact window activation in apps with multiple windows.

Post-MVP enhancement: app activation plus best-effort window raise if a native-safe path exists.

### Activation Outcomes

When Cmd+G is pressed:

- Gaze disabled: no activation; report disabled/not ready.
- No locked target: no activation; report no target.
- Target app already frontmost: no activation; report Already frontmost.
- Target exists and app is not frontmost: activate owning app.
- Activation unavailable/refused: report failure as recoverable status.

After successful activation:

- Show brief success flash/toast.
- Continue normal tracking.

Repeated activation is suppressed only when the target app is already frontmost. Otherwise, manual Cmd+G remains explicit user intent.

## Privacy and Diagnostics

### UI Privacy

MVP UI may show app names by default.

MVP UI and logs must not show window titles.

Examples:

- Allowed: Target: Safari.
- Allowed: Target: Terminal.
- Not allowed in MVP: Safari - Bank Statement.pdf.
- Not allowed in MVP: Cursor - secret-repo/main.py.

### Data Boundaries

Absolute MVP rule: Gaze must not persist, log, export, or display:

- Camera frames.
- Screenshots.
- Window titles.
- Raw desktop content.
- Raw visual/video payloads.

Camera/video data may only be processed transiently as needed by the tracker. Diagnostics and validation evidence are scalar-only.

### Scalar Diagnostics

Scalar diagnostics may include only numeric, boolean, enum, or timestamp-like fields such as:

- Calibration state.
- Confidence value.
- Lock duration.
- Activation success/failure.
- Already-frontmost count.
- No-target count.
- Display-layout-degraded event.
- Hotkey registration success/failure.

Default policy:

- Development builds: scalar diagnostics on.
- Release/default profile: scalar diagnostics off.

Manual validation should include a scalar session summary. It must not include frames, screenshots, window titles, or raw desktop content.

## Permissions

Request permissions just in time.

- Ask for camera permission when calibration starts.
- Do not ask for Accessibility permission unless a future feature truly requires it.
- Explain what Gaze does not do before permission requests: no recording, no screenshots, no clicks, manual activation only.

## Packaging

First slice may run with `make run`.

Local `.app` bundle comes after the fake prototype works. It must be present before beta-ready validation.

Signed/notarized distribution is out of MVP scope.

Launch-at-login is out of MVP scope.

## Explicit Exclusions

Not included in MVP:

- Auto-activation.
- Synthetic clicks or cursor movement.
- Dedicated panic hotkey; Disable and Option+Cmd+G are the MVP panic-stop path.
- Launch-at-login.
- Window titles in UI or logs.
- Cross-Space switching.
- Public/general beta onboarding.
- Signed/notarized distribution.
- Exact window activation promise.
- Per-app allow/deny automation policy.
- Dwell gestures.

## Open Follow-Up Decisions

These should not block the fake prototype:

1. Exact visual styling for icon variants.
2. Exact border/glow color and animation timing.
3. Whether scalar diagnostic schema should be JSONL, SQLite, or summary-only.
4. Whether local `.app` bundling uses py2app, briefcase, or a custom bundle script.
5. When to revisit post-MVP best-effort window raise.
