# Gaze

Gaze is a macOS native menu-bar app for gaze-assisted window focus. It uses PupilTracker for explicit webcam calibration and gaze estimation, shows a privacy-safe preview of the current target, and lets you press `Cmd+G` to bring the owning app forward.

The current MVP is trust-first. Nothing activates automatically by default. The app asks for calibration only when you choose it, avoids storing raw visual content, and keeps activation manual until the user has seen what Gaze thinks the target is.

## What works now

- Native macOS menu-bar runtime through PyObjC / AppKit.
- Explicit PupilTracker calibration with just-in-time camera permission. The Gaze-launched helper window can be closed/hidden after calibration without stopping the live scalar sample bridge.
- Gaze sample bridge from PupilTracker into Gaze's scalar state model.
- Visible-window candidate selection through CoreGraphics / Quartz.
- Privacy-safe current-target preview with no window titles or content-bearing labels in state, logs, docs, or diagnostics.
- Subtle non-interactive target border overlay.
- Global `Cmd+G` manual activation through Carbon hotkeys.
- AppKit activation by process identity, including already-frontmost suppression and no-target handling.
- Panic-safe disable path that hides overlays and blocks activation.
- Last-good calibration persistence for same-layout restarts.
- Scalar-only validation evidence export.
- Local unsigned `.app` bundle for realistic LaunchServices, status-item, and permission validation.

## Current beta posture

Gaze is beta-ready for the single-display manual-activation MVP path after local validation.

Validated evidence so far:

- `make check`: current branch automated gate.
- `make app-bundle`: builds `dist/Gaze.app` with bundled Python environment and MediaPipe model.
- `make smoke-app-status-item`: confirms the bundle launches as a native menu-bar app using scalar-only process and menu-bar geometry evidence.
- Optional developer-only PupilTracker validation can use `make check-pupil-dev` when changing the sibling tracker.
- Manual validation has covered launch, setup messaging, calibration, target preview, `Cmd+G` activation, no-target behavior, disable behavior, border toggling, privacy posture, and clean shutdown.

Known limitation:

- Built-in plus external display layout switching still needs hardware-backed manual validation. The current validation host exposes one active external main display.

## Calibration persistence

Earlier builds required recalibration after every restart because calibration lived only in memory. Current builds persist a local last-good calibration profile at:

```text
~/Library/Application Support/Gaze/last-good-calibration.json
```

This profile is scalar-only. It stores display-layout geometry/signature and readiness metadata, not camera frames, screenshots, window titles, URLs, filenames, or raw desktop content.

Startup behavior:

- If the current display layout matches the saved profile, Gaze restores calibration as degraded-but-usable.
- The first fresh valid gaze sample promotes readiness back to ready.
- If the display layout changes, Gaze does not restore the profile and asks for recalibration.

## Privacy posture

Gaze is built around content-safe evidence and state:

- No screenshots, video frames, raw desktop captures, window titles, URLs, filenames, or content-bearing labels are persisted.
- Runtime state stores generic target summaries and scalar readiness information.
- Diagnostics are scalar-only and release-disabled by default.
- Smoke tests report process presence, status-item geometry, and counts only.
- Camera access is requested only when calibration explicitly starts.
- Accessibility and Input Monitoring permissions are not required for the current manual-activation MVP path.

## Tech stack

- Python 3.11+
- PyObjC / AppKit for the native macOS app shell
- CoreGraphics / Quartz for visible-window metadata
- Carbon for global hotkey registration
- PupilTracker for calibration and gaze samples
- pytest, ruff, and ty for checks
- uv for dependency management

## Repo structure

- `src/gaze/app.py` — AppKit application bootstrap and runtime composition
- `src/gaze/core/` — side-effect-free app state, trust preview, target policy, and diagnostics
- `src/gaze/tracking/` — PupilTracker adapter boundary
- `src/gaze/desktop/` — window candidates, display geometry, and activation seams
- `src/gaze/overlays/` — border and heatmap overlay boundaries
- `src/gaze/hotkeys/` — global hotkey binding boundary
- `src/gaze/settings/` — local scalar settings and calibration profile persistence
- `src/gaze/ui/` — setup window and menu-bar controllers
- `tests/` — fast tests using fakes only
- `docs/product/` — PRD and product scope
- `docs/plans/` — execution task graphs
- `docs/validation/` — beta-readiness review, manual checklist, and scalar validation evidence

## Local setup

Default release-style development setup uses the PyPI dependency declared in `pyproject.toml`:

```bash
make sync
make check
```

PUPIL_TRACKER_PATH is not required for normal private beta use. Use the default bundle path first:

```bash
make app-bundle
open dist/Gaze.app
```

For source-tree development against an editable sibling checkout, use the explicit developer targets only when changing or validating local PupilTracker internals:

```bash
make sync-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

Use `check-pupil-dev` or `run-pupil-dev` after editable setup. Those targets pass `uv run --no-sync` so uv does not silently revert the environment back to the locked PyPI package before execution.

If `PUPIL_TRACKER_PATH` is not provided to a developer target, the target assumes a project-local sibling at `../pupil-tracker`. This does not affect normal `make app-bundle` use.

For developer runs that also override the MediaPipe model path:

```bash
(cd /Users/sage/workspace/sagebynature/pupil-tracker && make download-model)
PUPIL_TRACKER_MEDIAPIPE_MODEL=/Users/sage/workspace/sagebynature/pupil-tracker/models/face_landmarker.task \
  make run-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

## Local `.app` bundle

Build a local unsigned development bundle for realistic macOS launch and permission validation. The default bundle installs Gaze with the PyPI/release `pupil-tracker` dependency declared in `pyproject.toml` and downloads the MediaPipe FaceLandmarker model into the app bundle:

```bash
make app-bundle
open dist/Gaze.app
```

For the explicit editable sibling PupilTracker workflow only, use:

```bash
make app-bundle-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
open dist/Gaze.app
```

The local bundle is intentionally unsigned and not notarized. It embeds a Python environment under `dist/Gaze.app/Contents/Resources/.venv`, bundles the model at `dist/Gaze.app/Contents/Resources/models/face_landmarker.task`, and writes a local operator note at `dist/Gaze.app/Contents/Resources/README-local-app.txt`.

After building the bundle, run the privacy-safe LaunchServices status-item smoke before manual validation:

```bash
make smoke-app-status-item
```

The smoke emits scalar-only process, menu-bar geometry, and status-scene counts. It does not persist screenshots, frames, window titles, URLs, or raw desktop content.

## Running from source

Launch the app from source:

```bash
make run
```

For editable PupilTracker development:

```bash
make run-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

The app remains import-safe: importing `gaze.app` does not start the camera, enumerate windows, register hotkeys, or activate apps.

## Daily validation commands

Use these before claiming the local app is ready:

```bash
make check
make app-bundle
make smoke-app-status-item
```

Optional developer-only sibling validation:

```bash
make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

Repo convention: remove `uv.lock` before committing Gaze changes.
