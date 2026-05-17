# Gaze

Gaze is a macOS native menu-bar app for gaze-assisted window focus. It uses explicit webcam calibration, scalar-only gaze state, and manual `Cmd+G` activation to bring the owning app for the current target forward.

The private beta posture is trust-first:

- Camera access is requested only when calibration explicitly starts.
- No screenshots, video frames, window titles, URLs, filenames, or raw desktop content are stored.
- The default local app bundle uses release dependencies and a bundled MediaPipe model.
- Normal private beta validation uses `make app-bundle`, then `open dist/Gaze.app`.

Developer setup and editable dependency workflows are documented in the repository README, not in packaged app metadata.
