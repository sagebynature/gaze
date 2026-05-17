# Gaze Beta-Ready Review

Slice: GAZE-045
Gate: Gate 4 - Beta-ready for Sage

## Decision

Decision: not beta-ready for daily-driver validation until manual evidence passes.

Rationale: the automated trust chain is in place and the evidence path exists, but the final Sage-only daily-driver decision requires a completed manual checklist plus scalar summary export from the real local `.app` workflow. This review records the current state and blocks promotion until that evidence is filled in.

## Automated Evidence

Status: automated checks pass.

Required commands:

- `make check`
- `make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker`

These gates cover import safety, fake prototype behavior, real trust preview seams, local `.app` builder behavior, editable hotkeys, scalar diagnostics, trust surface polish, beta evidence export, and privacy guards.

## Known Blocking Evidence

The following evidence and fixes must be completed before changing the decision to beta-ready:

- Manual checklist: complete `docs/validation/beta-ready-manual-validation.md`.
- Scalar summary export: attach or paste the `gaze.scalar-summary.v1` JSON text from the validation run.
- Hermes/agent cockpit: validate the primary coding cockpit workflow with scalar notes only.
- Built-in + external display layouts: validate the variable display setups with scalar layout labels only.
- Failure paths: confirm unavailable activation, no target, degraded calibration, and hotkey conflict behavior.
- Privacy checks: confirm no visual captures, tracker image data, content-bearing labels, URLs, desktop details, or window titles are recorded.
- Default release/PyPI bundle Recalibrate must show actionable guidance when the desktop calibration source is unavailable.
- Cmd+G must work as a true global hotkey or be explicitly downgraded from the beta-ready acceptance path.
- Toggle Heatmap must either render a session-local input-transparent heatmap or clearly report that it is unavailable.

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

- auto-activation
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
