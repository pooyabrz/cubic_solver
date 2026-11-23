# CUBIQ Studio — Mouse-first Rubik's Cube Solver

A redesigned version of the original `cubic_solver` project. The application has a **single-window desktop UI**: 3D cube, clickable turns, a six-face sticker editor, solution playback, a visible help guide, and reliable state handling.

## Quick start

Use **Python 3.10–3.12** and a normal desktop environment (Windows, macOS or Linux). An active display is required.

```bash
python -m pip install -r requirements.txt
python main.py
```

On Windows, you can instead double-click `start_windows.bat` to prepare a virtual environment and launch the app. On macOS/Linux, run `bash start_unix.sh`. The first run of either script needs internet access to install dependencies.

### What changed?

| Before | CUBIQ Studio |
|---|---|
| Commands visible only in README/console | **Clickable, labeled buttons** and on-screen tips |
| Flat, sequential 9-key-per-face color input | **Click-to-paint 54-sticker net** with a color palette |
| Mouse drag to rotate the 3D camera only | **Mouse drag, scroll zoom, clickable stickers and zoom buttons** |
| No on-screen solution steps | **Progress bar, move chips, step back/next, play/pause, speed control** |
| Reset could lose manual work | **Undo/redo**, reversible reset and scramble |
| Loose face-to-3D mapping | **One canonical 3D coordinate system for turns, net, and visualization** |
| Invalid input mostly exposed in the terminal | **In-app validation and explanatory error messages** |
| Required OpenGL and NumPy | **Only Pygame for graphics and Kociemba for solutions** |

## Guide

1. **Turn the cube**: Click the `U R F D L B` buttons below the 3D view. The second row turns in the opposite direction. The single letters are standard Rubik's notation (not colors).
2. **Rotate / zoom the view**: Left- or right-drag the cube area to orbit. Use the mouse wheel or `+` / `-` buttons to zoom. `Reset view` restores the default camera.
3. **Paint a custom configuration**: Click a color in the editor palette (this enables Paint mode), then click a tile in the unfolded net—or a visible sticker on the 3D cube. All six faces are in the net. Center squares are locked because their positions are fixed on a standard 3x3 cube. Click `Paint: ON` to stop painting.
4. **Scramble / solve**: Click `Scramble`, then `Find solution`. The solver creates a plan but does **not** immediately alter the cube. Click `Play / Resume` to play, or `Next` / `< Back` to move one turn at a time. Click a move chip to jump directly to that step. Use `+/-` in the solution panel to adjust pace.
5. **Import / export / save**: Click `Import / Export` in the top bar to copy, paste or type a standard 54-character string. A session can also be saved to the local user's home folder and later restored.
6. **Help**: `? How to use` opens the built-in onboarding guide at any time.


### Keyboard shortcuts (optional)

| Shortcut | Action |
|---|---|
| `U`, `R`, `F`, `D`, `L`, `B` | Clockwise face move |
| `Shift` + face letter | Counterclockwise face move |
| `S` | Scramble |
| `X` | Reset cube |
| `E` | Toggle paint mode |
| `Space` | Play / pause solution |
| `N` / `P` | Next / previous solution step |
| Arrow keys | Orbit camera |
| `H`, `F1`, or `Esc` | Open help (`Esc` also closes modal dialogs) |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo manual changes |
| `Ctrl+S` / `Ctrl+O` | Save / load local session |
| `Ctrl+I` | Import/export window |
| `Ctrl+Q` | Quit |

**Shortcut change:** The original application used `R` for Reset. In this version `R` turns the **Right** face, and `X` resets the cube. This avoids a conflict with standard face notation.

## Cube colors and notation

The default color convention is:

| Face | Up `U` | Right `R` | Front `F` | Down `D` | Left `L` | Back `B` |
|---|---|---|---|---|---|---|
| Color | White | Blue | Red | Yellow | Green | Orange |

The 54-letter string is ordered **U, R, F, D, L, B**, each face in row-major order. Each letter identifies the face whose center has that color. Example, solved cube:

```text
UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
```

Imported states are checked for length, allowed letters, centers, and color counts. If `kociemba` is installed, imported states are also verified for physical solvability. A manually painted cube with nine stickers of each color can nevertheless be physically impossible (twisted corner, flipped edge, permutation parity). The app reports Kociemba's error rather than silently trying to animate an invalid solution.

## Files

```text
cubic_solver-main/
├── main.py                 # responsive, mouse-driven pygame application
├── cube_model.py           # deterministic, geometry-correct cube model
├── cube_visualizer.py      # lightweight 3D software renderer + picking
├── solver.py               # Kociemba integration / solver errors
├── requirements.txt        # 2 dependencies
├── start_windows.bat       # automatic Windows setup / run
├── start_unix.sh           # automatic Linux/macOS setup / run
├── tests/
│   └── test_cube_model.py  # model and solver tests
├── CHANGELOG.md
└── README.md
```

Session files are stored at:

- Windows: `C:\Users\<your-user>\.cubiq-studio\session.json`
- Linux / macOS: `~/.cubiq-studio/session.json`

They contain only locally entered cube stickers, camera angle and play speed. No network service or user account is required by the app itself; the Kociemba solver runs locally.

## Testing

Core-model tests require only Python's standard library. If Kociemba is installed, they also test an actual solve.

```bash
python -m unittest discover -s tests -v
```

## Troubleshooting

- **`No module named pygame`**: Install the dependencies with `python -m pip install -r requirements.txt` using the same Python interpreter used to run the program.
- **`Solver not installed`**: Make sure the `kociemba` dependency installed successfully. A Python 3.10–3.12 virtual environment is recommended.
- **Display won't open**: Run it on a desktop with a graphical session. Remote text-only servers and headless CI systems cannot open the Pygame window directly.
- **Colors balanced but cube won't solve**: The sticker configuration may be physically impossible. Check all six faces against your real cube, particularly piece orientation.
- **Window too small**: Resize the window; the interface scales uniformly and preserves its aspect ratio. A desktop window of approximately 1280×800 or larger is recommended.

## Design note

The original OpenGL visualizer placed colors on cubies using several approximate special-case index mappings. CUBIQ instead defines a face basis for each side and uses it to calculate sticker positions, legal layer permutations, and projected 3D polygons. That removes an entire class of color/orientation inconsistencies. No manual editing or key input modifies the fixed centers in the standard editor.
