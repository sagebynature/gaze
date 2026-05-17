# GAZE-040 Local App Bundle Checklist

Slice: GAZE-040
Scope: local unsigned `.app` bundle for realistic lifecycle and permissions validation.

## Automated Gate

- [x] `uv run pytest tests/test_local_app_bundle.py -v`
- [x] `make check`
- [x] `make app-bundle-pupil-dev PUPIL_TRACKER_PATH=/Users/sage/workspace/sagebynature/pupil-tracker`

## Bundle Structure

- [x] `dist/Gaze.app/Contents/Info.plist` exists.
- [x] `CFBundleExecutable` is `Gaze`.
- [x] `LSUIElement` is enabled for menu-bar app posture.
- [x] `NSCameraUsageDescription` explains camera use is explicit-calibration only.
- [x] `GazeDistributionScope` is `local-unsigned`; signing/notarization stays out of scope.
- [x] `dist/Gaze.app/Contents/MacOS/Gaze` is executable.
- [x] `dist/Gaze.app/Contents/Resources/.venv/bin/python` exists after non-dry-run build.
- [x] `dist/Gaze.app/Contents/Resources/README-local-app.txt` exists.

## Manual Smoke

- [x] `open dist/Gaze.app` launches the menu-bar app outside the source tree.
- [x] Embedded environment imports `gaze` from bundle site-packages while current directory is outside the source tree.
- [x] Missing model/dependency failure message is actionable.
- [ ] Camera prompt appears only after explicit Recalibrate/calibration start.
- [ ] Recalibrate does not implicitly enable Gaze tracking; enable Gaze separately for live border preview.

## Privacy Gate

- [x] No screenshots are persisted.
- [x] No frames are persisted.
- [x] No window titles, document names, URLs, or raw desktop content are persisted.
