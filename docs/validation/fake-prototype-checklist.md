# Gaze Fake Prototype Validation Checklist

Date: 2026-05-16 00:26:25 EDT
Operator: Sage
Commit: d6c2c3d

## Automated Gate

- [x] `make check` passes.

## Import Safety

- [x] Importing `gaze.app` does not start camera access.
- [x] Importing `gaze.app` does not enumerate windows.
- [x] Importing `gaze.app` does not register hotkeys.
- [x] Importing `gaze.app` does not draw overlays.
- [x] Importing `gaze.app` does not activate apps.

## Menu-Bar Utility Shape

- [x] App launches as menu-bar utility.
- [x] No persistent dashboard window opens by default.
- [x] Menu includes status, target app/no target, confidence, enable/disable, border, heatmap, recalibrate, settings, Developer panel in development mode, quit.
- [x] Menu actions call the same command seams used by tests.
- [x] Menu shows app names only; no window titles.

## Setup and Developer Panel

- [x] Settings window opens only from menu action.
- [x] Developer panel is separate from setup/settings.
- [x] Developer panel is development-gated.
- [x] Scripted fake sequence can run.
- [x] Manual fake target can be selected.
- [x] Fake frontmost app can be set.
- [x] No-target state can be triggered.
- [x] Activation failure state can be triggered.
- [x] Degraded state can be triggered.

## Border Overlay

- [x] Border appears around fake target bounds after lock.
- [x] Border hides on no-target.
- [x] Border hides on disable.
- [x] Border does not intercept mouse clicks.
- [x] Border does not steal key focus.

## Activation Seam

- [x] Cmd+G/activation command does nothing while disabled.
- [x] Cmd+G/activation command reports no target when no target is locked.
- [x] Cmd+G/activation command reports Already frontmost when fake target is frontmost.
- [x] Cmd+G/activation command reports success for non-frontmost locked fake target.
- [x] Activation failure shows subtle status/toast, not a modal.

## Panic Disable

- [x] Disable clears target.
- [x] Disable hides overlay.
- [x] Disable blocks activation.

## Privacy

- [x] No screenshots are saved.
- [x] No camera frames are saved.
- [x] No window titles are shown or logged.
- [x] No raw desktop content is logged/exported.

Validation note: User manually validated the local AppKit runtime after commit d6c2c3d; all checklist items reported green.
