# 🧩 Rubik’s Cube 3D Solver — Pygame + OpenGL + Kociemba

A full 3D interactive **Rubik’s Cube simulator and solver**, built with **Python, Pygame, and PyOpenGL**, featuring:
- Realistic 3D rendering
- Manual coloring & editing mode
- Step-by-step or automatic solving
- Integration with the **Kociemba two-phase algorithm**

---

## 🚀 Features

### 🎮 Core Controls
| Key | Action |
|-----|--------|
| **Mouse Drag** | Rotate the camera around the cube |
| **Arrow Keys** | Rotate the camera (alternative) |
| **Space** | Automatic solve animation |
| **N** | Step-by-step solve (press repeatedly) |
| **S** | Generate a random scramble |
| **R** | Reset cube to solved state |
| **E** | Enter/exit edit (color input) mode |
| **ESC** | Quit |

---

### 🧱 Edit Mode (Custom Coloring)
Press **E** to enter edit mode.

Then:
1. You’ll cycle through faces in this order:  
   **U → R → F → D → L → B**
2. Use color keys to fill each sticker:
   | Key | Color | Face |
   |------|--------|-------|
   | `W` | White | U |
   | `Y` | Yellow | D |
   | `R` | Red | F |
   | `O` | Orange | B |
   | `G` | Green | L |
   | `B` | Blue | R |
3. `Enter` saves the face and moves to the next one.
4. After all 6 faces, edit mode exits automatically and normal solving becomes available.

Each face’s **center color** is used to define which side is U, D, F, B, L, R for the solver — so you can use any color-to-side mapping you want.

---

### 🧠 Solving Logic

The solver is powered by the [Kociemba algorithm](https://github.com/muodov/kociemba), which requires the cube’s flattened state string in standard orientation order:
U (Up) → R (Right) → F (Front) → D (Down) → L (Left) → B (Back)

Internally, the project uses the function `cube.normalize_state_for_solver()` to:
- Read the **center colors** of each face,
- Map all stickers back to logical faces (U, R, F, D, L, B),
- Generate a valid 54-character state string for Kociemba.

Example:
UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB

---

## 🧩 Project Architecture
rubiks_solver/

│

├── main.py # Main loop: rendering, input, event handling

├── cube_model.py # Cube state logic & mapping

├── cube_visualizer.py # OpenGL rendering code

└── solver.py # Kociemba integration & step control

### Key Components

#### `cube_model.py`
- Full 3D cube data model (6 faces × 3×3 stickers)
- Verified move logic (`U`, `D`, `F`, `B`, `L`, `R`, and their `'`, `2` variants)
- **normalize_state_for_solver()** — maps face colors properly for Kociemba

#### `cube_visualizer.py`
- PyOpenGL + Pygame rendering of a 3D cube
- Camera controls and rotation logic

#### `solver.py`
- Calls `cube.normalize_state_for_solver()` to get the correct state string
- Uses `kociemba.solve()` to generate the move sequence
- Supports continuous (`Space`) and step-by-step (`N`) solving

#### `main.py`
- Main event loop and keyboard handling
- Edit mode logic for manual coloring
- Integrates all modules cleanly

---

## 🧰 Installation

### Clone the repo
```bash
git clone https://github.com/ali-jahan/rubiks-3d-solver.git
cd rubiks-3d-solver

bash
pip install -r requirements.txt

bash
python main.py