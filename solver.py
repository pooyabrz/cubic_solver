"""Kociemba's two-phase solver, kept separate from the UI."""

try:
    import kociemba
except ImportError:
    kociemba = None


def solve_cube(cube):
    try:
        state = cube.normalize_state_for_solver()
        if cube.is_solved():
            return [], None
        if kociemba is None:
            return None, "Solver not installed. Run: pip install -r requirements.txt"
        # A physically impossible but color-balanced hand-painted state is
        # reported here by Kociemba (edge flips, corner twists, parity, etc).
        solution = kociemba.solve(state)
        return solution.split(), None
    except Exception as exc:
        return None, "Cube cannot be solved: " + str(exc)
