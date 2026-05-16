# Gaze Fake Prototype Validation Checklist

Date:
Operator: Sage
Commit:

## Automated Gate

- [ ] `make check` passes.

## Import Safety

- [ ] Importing `gaze.app` does not start camera access.
- [ ] Importing `gaze.app` does not enumerate windows.
- [ ] Importing `gaze.app` does not register hotkeys.
- [ ] Importing `gaze.app` does not draw overlays.
- [ ] Importing `gaze.app` does not activate apps.

## Menu-Bar Utility Shape

- [ ] App launches as menu-bar utility.
- [ ] No persistent dashboard window opens by default.
- [ ] Menu includes status, target app/no target, confidence, enable/disable, border, heatmap, recalibrate, settings, Developer panel in development mode, quit.
- [ ] Menu actions call the same command seams used by tests.
- [ ] Menu shows app names only; no window titles.

## Setup and Developer Panel

- [ ] Settings window opens only from menu action.
- [ ] Developer panel is separate from setup/settings.
- [ ] Developer panel is development-gated.
- [ ] Scripted fake sequence can run.
- [ ] Manual fake target can be selected.
- [ ] Fake frontmost app can be set.
- [ ] No-target state can be triggered.
- [ ] Activation failure state can be triggered.
- [ ] Degraded state can be triggered.

## Border Overlay

- [ ] Border appears around fake target bounds after lock.
- [ ] Border hides on no-target.
- [ ] Border hides on disable.
- [ ] Border does not intercept mouse clicks.
- [ ] Border does not steal key focus.

## Activation Seam

- [ ] Cmd+G/activation command does nothing while disabled.
- [ ] Cmd+G/activation command reports no target when no target is locked.
- [ ] Cmd+G/activation command reports Already frontmost when fake target is frontmost.
- [ ] Cmd+G/activation command reports success for non-frontmost locked fake target.
- [ ] Activation failure shows subtle status/toast, not a modal.

## Panic Disable

- [ ] Disable clears target.
- [ ] Disable hides overlay.
- [ ] Disable blocks activation.

## Privacy

- [ ] No screenshots are saved.
- [ ] No camera frames are saved.
- [ ] No window titles are shown or logged.
- [ ] No raw desktop content is logged/exported.
