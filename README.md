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

```bash
make sync
make check
```

Launch the current skeleton app:

```bash
make run
```

The skeleton is intentionally safe: it does not start the camera, enumerate windows, register hotkeys, or activate apps on import.
