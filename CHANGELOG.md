# Changelog

## 2.0 — Desktop UX redesign

- Replaced the keyboard-only main loop with a complete mouse-operated studio interface.
- Added quick actions (scramble/reset/solve/play/undo/redo), hover labels, feedback toasts, 3D zoom buttons and an in-app guide.
- Added click-to-paint unfolded cube net, color palette, and direct on-cube sticker picking; centers protected.
- Added solver roadmap, progress display, move-chip navigation, step back/next, play/pause and adjustable timing.
- Added safe local session save/restore and import/export of URFDLB facelets.
- Added fast validation of color counts and center uniqueness, with Kociemba validation for imported states when available.
- Replaced OpenGL cube geometry with a pygame software renderer using an exact face-basis mapping.
- Replaced six duplicated hand-coded rotation routines with an explicit 3D coordinate rotation model for all 18 standard moves.
- Removed PyOpenGL, PyOpenGL-accelerate and NumPy requirements.
- Added 13 test cases and platform launch scripts.
- Added bilingual usage guidance in README and documented updated keyboard shortcuts.

### Operational limits

- Animated solving plays discrete turns at a controlled pace; cubie rotations are not interpolated smoothly between states.
- Pygame text input and clipboard integration depend on the desktop/window manager and may differ by OS.
- Full UI smoke testing requires a desktop with pygame installed. Core logic tests run without a display or dependencies.
