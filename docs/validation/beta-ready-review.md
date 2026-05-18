# Gaze Beta-Ready Review

Slice: GAZE-045
Gate: Gate 4 - Beta-ready for Sage

## Decision

Decision: implementation-complete for the private beta MVP path, but not fully promoted for daily-driver validation until the remaining hardware-dependent display-layout evidence is captured.

Rationale: the automated trust chain is in place, the default app bundle launches and smokes cleanly, default packaged Recalibrate now launches the calibration provider without `PUPIL_TRACKER_PATH`, the locked-target Cmd+G evidence path passes, and the scalar summary export is attached. The final Sage-only daily-driver promotion still requires built-in + external display-layout evidence that was not available on the current hardware state.

## Automated Evidence

Status: automated checks pass.

Required commands:

- `make check`
- `make app-bundle`
- `make smoke-app-status-item`
- user-facing bundle artifact scan for developer-path guidance
- packaged runtime Recalibrate launch probe from the default bundle

Optional developer-only command, not rerun in the final default-bundle closeout:

- `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker`

These gates cover import safety, fake prototype behavior, real trust preview seams, local `.app` builder behavior, editable hotkeys, scalar diagnostics, trust surface polish, beta evidence export, privacy guards, default bundle launch, packaged calibration-provider availability, and beta-safe fallback guidance.

## Known Blocking Evidence

The following evidence and fixes must be completed before changing the decision to beta-ready:

- Manual checklist: complete `docs/validation/beta-ready-manual-validation.md`.
- Scalar summary export: attached in `docs/validation/beta-ready-manual-validation.md` from the locked-target Cmd+G validation run.
- Hermes/agent cockpit: validate the primary coding cockpit workflow with scalar notes only.
- Built-in + external display layouts: validate the variable display setups with scalar layout labels only.
- Failure paths: confirm unavailable activation, no target, degraded calibration, and hotkey conflict behavior.
- Privacy checks: confirm no visual captures, tracker image data, content-bearing labels, URLs, desktop details, or window titles are recorded.
- Default bundle Recalibrate launches the packaged calibration provider when the adjacent packaged PupilTracker checkout is available, without `PUPIL_TRACKER_PATH` or editable runtime overrides.
- 2026-05-17 re-run evidence: rebuilt default `dist/Gaze.app`, confirmed `desktop_demo.app` is importable inside the bundle environment, passed status-item smoke, clicked Recalibrate through the live menu, observed one calibration child subprocess, and observed no new crash report.
- Cmd+G has Carbon global hotkey registration plus scalar probe evidence; locked-target bundle revalidation is complete.
- 2026-05-17 re-run evidence: rebuilt `dist/Gaze.app`, verified the package environment used `CarbonGlobalHotkeyRegistry` with zero registration feedback, sent Cmd+G against a locked target, and observed activation_success with activation_count=1.
- Toggle Heatmap now clearly reports unavailable when no visible overlay is wired; a rendered session-local heatmap remains optional future polish rather than a silent beta blocker.
- Display-layout evidence remains hardware-blocked in this run: active display inspection reported one external main display only, so built-in + external layout A/B switching could not be manually validated.
- Same-layout restart recalibration burden is addressed in code: last-good calibration is persisted as scalar-only display-layout state and restored as degraded-but-usable until a fresh valid sample promotes readiness.
- 2026-05-17 final closeout on local `main` at `a488630`: `make check` passed with ruff clean, ty clean, and 194 pytest tests; `make app-bundle` rebuilt `dist/Gaze.app`; `make smoke-app-status-item` passed with native launcher parent, Python child, visible status item, and zero status-scene errors.
- 2026-05-17 final default-bundle scan: no `PUPIL_TRACKER_PATH`, `app-bundle-pupil-dev`, `/path/to/pupil-tracker`, `make sync-pupil-dev`, or `make run-pupil-dev` strings were present in user-facing `README-local-app.txt` or package metadata.
- 2026-05-17 final packaged runtime probe from the default bundle launched calibration successfully with one calibration child process and no new crash report.

## Required Manual Scope

The manual checklist must cover:

- fake prototype safety baseline
- real trust preview path
- local `.app` launch and lifecycle
- permissions requested just in time
- hotkeys with default, disabled, rebound, conflict, and unavailable states
- calibration ready, degraded, and retry behavior
- target border lock timing
- heatmap off-by-default, session-local, and clearable behavior
- Cmd+G activation behavior
- disable/panic behavior
- failure paths
- display layout changes
- privacy checks

## App Coverage

Validation evidence must cover Hermes/agent cockpit usage and the daily switching matrix:

- Hermes/agent cockpit
- Terminal/iTerm
- Browser/docs
- Discord
- AI/chat
- Repo editor

Record only pass/fail, category, display layout label, activation outcome, counts, calibration state, and short generic scalar notes.

## Display Coverage

Validation evidence must cover built-in + external display layouts:

- built-in only
- built-in + external display layout A
- built-in + external display layout B

Changing layouts must degrade calibration and recommend recalibration before a new trusted run.

## Out of Scope

The following remain out of MVP and must not be treated as beta blockers:

- auto-activation enabled by default
- synthetic clicks
- launch-at-login
- window titles
- cross-Space switching
- signed/notarized distribution
- best-effort individual window raise beyond owning-app activation

## Promotion Rule

Change this decision to beta-ready only after:

1. automated checks pass,
2. the manual checklist passes or known issues are documented,
3. the scalar summary export is content-safe,
4. Hermes/agent cockpit validation is covered, and
5. built-in + external display layout validation is covered.

Until then, Gaze remains implementation-complete for the beta-ready MVP path, but not approved for daily-driver validation.
