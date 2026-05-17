# Gaze

Gaze is a macOS native desktop app for gaze-assisted window focus. It uses PupilTracker for calibration and gaze estimation, then lets the user look at a window and press Cmd+G to bring the owning app forward.

The MVP is trust-first: calibration, current-target preview, subtle border overlay, optional heatmap, and manual activation before any auto-activation behavior.

## Tech stack

- Python 3.11+
- PyObjC / AppKit for the native macOS app shell
- CoreGraphics / Quartz for visible-window metadata
- PupilTracker for webcam calibration, gaze samples, heatmap primitives, and macOS window helper patterns
- pytest, ruff, and ty for checks
- uv for dependency management

## Repo structure

- `src/gaze/app.py` — AppKit application bootstrap
- `src/gaze/core/` — side-effect-free app state and policies
- `src/gaze/tracking/` — PupilTracker adapter boundary
- `src/gaze/desktop/` — window candidates and activation seams
- `src/gaze/overlays/` — border and heatmap overlay boundaries
- `src/gaze/hotkeys/` — global hotkey binding boundary
- `src/gaze/settings/` — local settings persistence boundary
- `src/gaze/ui/` — setup window and menu bar controllers
- `tests/` — fast tests using fakes only
- `docs/product/` — PRD and product scope
- `docs/plans/` — execution task graphs

## Local setup

Default release-style development setup uses the PyPI dependency declared in `pyproject.toml`:

```bash
make sync
make check
```

During real trust preview work, use the editable sibling PupilTracker checkout when you need local calibration or gaze changes without publishing a package:

```bash
make sync-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
make check-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

Use `check-pupil-dev` or `run-pupil-dev` after editable setup; those targets pass `uv run --no-sync` so uv does not silently revert the environment back to the locked PyPI package before execution.

For source-tree development against an editable sibling checkout, provide both the sibling checkout and the MediaPipe model path. If the model is missing, download it from the PupilTracker checkout first:

```bash
(cd /Users/sage/workspace/sagebynature/pupil-tracker && make download-model)
PUPIL_TRACKER_MEDIAPIPE_MODEL=/Users/sage/workspace/sagebynature/pupil-tracker/models/face_landmarker.task \
  make run-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker
```

If `PUPIL_TRACKER_PATH` is not provided, the target assumes a project-local sibling at `../pupil-tracker`.

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

Required permission posture:

- Camera is requested only when calibration explicitly starts.
- Accessibility/Input Monitoring are not required for the current MVP path.
- The launcher and docs must not persist screenshots, frames, window titles, content-bearing labels, URLs, or raw desktop content.

Launch the current skeleton app:

```bash
make run
```

The skeleton is intentionally safe: it does not start the camera, enumerate windows, register hotkeys, or activate apps on import.
