try:
    import kociemba
except ImportError:
    kociemba = None

def solve_cube(cube):
    if not kociemba:
        return None, "Kociemba library not installed (pip install kociemba)"
    
    try:
        # Get string like 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        state_str = cube.normalize_state_for_solver()
        
        # Solve
        solution_str = kociemba.solve(state_str)
        
        # Return list of moves
        return solution_str.split(), None
    except Exception as e:
        return None, str(e)
