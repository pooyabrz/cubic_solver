"""A consistent, testable Rubik's cube model (no graphics dependencies).

Face positions and moves use the same right-handed 3-D coordinate system.
Consequently the displayed stickers and the Kociemba facelet string agree.
"""

from __future__ import annotations

import random
from collections import Counter
from copy import deepcopy

FACES = ("U", "R", "F", "D", "L", "B")
FACE_COLOR = {"U": 0, "D": 1, "F": 2, "B": 3, "L": 4, "R": 5}
COLOR_NAMES = ("White", "Yellow", "Red", "Orange", "Green", "Blue")

# (outward normal, right on face, up on face), as seen from outside.
FACE_BASIS = {
    "U": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "R": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "F": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "D": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "L": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "B": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
}
NORMAL_TO_FACE = {basis[0]: f for f, basis in FACE_BASIS.items()}


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def add_scaled(a, b, scale):
    return tuple(x + scale * y for x, y in zip(a, b))


def sticker_position(face, row, column):
    """Integer cubie position of a sticker, with -1/0/+1 coordinates."""
    normal, right, up = FACE_BASIS[face]
    return add_scaled(add_scaled(normal, right, column - 1), up, 1 - row)


def slot_from_geometry(position, normal):
    """Inverse mapping for a moved sticker (position, outward normal)."""
    face = NORMAL_TO_FACE[normal]
    _, right, up = FACE_BASIS[face]
    return face, 1 - dot(position, up), 1 + dot(position, right)


def rotate_90(vector, axis, direction):
    """Rotate an integer vector 90 degrees around a positive coordinate axis.

    direction=+1 follows right-hand rule; -1 is the opposite.
    """
    x, y, z = vector
    if axis == 0:
        return (x, -direction * z, direction * y)
    if axis == 1:
        return (direction * z, y, -direction * x)
    return (-direction * y, direction * x, z)


def inverse_move(move):
    if move.endswith("2"):
        return move
    return move[:-1] if move.endswith("'") else move + "'"


class RubiksCube:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = {
            face: [[FACE_COLOR[face]] * 3 for _ in range(3)]
            for face in FACES
        }

    def snapshot(self):
        return deepcopy(self.state)

    def restore(self, snapshot):
        if set(snapshot) != set(FACES):
            raise ValueError("Invalid snapshot: expected all six faces")
        self.state = deepcopy(snapshot)

    def execute_move(self, move):
        """Execute a standard Singmaster move, including apostrophe and 2."""
        if not isinstance(move, str) or not move or move[0] not in FACES or move[1:] not in ("", "'", "2"):
            raise ValueError(f"Unknown move: {move!r}")
        face = move[0]
        normal = FACE_BASIS[face][0]
        axis = next(i for i, value in enumerate(normal) if value)
        sign = normal[axis]
        # A clockwise turn as viewed from outside is -90 degrees about the
        # face's OUTWARD normal. We rotate about the positive axis instead.
        direction = -sign * (-1 if move.endswith("'") else 1)
        for _ in range(2 if move.endswith("2") else 1):
            old = self.snapshot()
            updated = self.snapshot()
            for old_face in FACES:
                old_normal = FACE_BASIS[old_face][0]
                for row in range(3):
                    for col in range(3):
                        position = sticker_position(old_face, row, col)
                        if position[axis] != sign:
                            continue
                        next_position = rotate_90(position, axis, direction)
                        next_normal = rotate_90(old_normal, axis, direction)
                        target_face, target_row, target_col = slot_from_geometry(next_position, next_normal)
                        updated[target_face][target_row][target_col] = old[old_face][row][col]
            self.state = updated

    def apply_moves(self, moves):
        for move in moves:
            self.execute_move(move)

    def scramble(self, n=25, rng=None):
        rng = rng if rng is not None else random
        moves = []
        last_face = None
        axes = {"U": 0, "D": 0, "R": 1, "L": 1, "F": 2, "B": 2}
        last_axis = None
        for _ in range(n):
            candidates = [f for f in FACES if f != last_face and axes[f] != last_axis]
            face = rng.choice(candidates)
            move = face + rng.choice(("", "'", "2"))
            moves.append(move)
            self.execute_move(move)
            last_face, last_axis = face, axes[face]
        return moves

    def set_sticker(self, face, row, column, color, allow_center=False):
        if face not in FACES or not (0 <= row < 3 and 0 <= column < 3):
            raise ValueError("Unknown sticker")
        if color not in range(6):
            raise ValueError("Unknown color")
        if (row, column) == (1, 1) and not allow_center:
            raise ValueError("Center stickers are fixed; rotate the cube instead")
        self.state[face][row][column] = color

    def set_face_from_list(self, face, color_list):
        if face not in FACES or len(color_list) != 9 or any(v not in range(6) for v in color_list):
            raise ValueError("A face requires exactly 9 valid colors")
        self.state[face] = [list(color_list[i:i + 3]) for i in range(0, 9, 3)]

    def validate(self):
        """Fast checks before asking Kociemba to check physical solvability."""
        counts = Counter()
        centers = []
        for face in FACES:
            for row in self.state[face]:
                if len(row) != 3:
                    return False, "Every face must have 9 stickers."
                for color in row:
                    if color not in range(6):
                        return False, "A sticker has an unrecognized color."
                    counts[color] += 1
            centers.append(self.state[face][1][1])
        if len(set(centers)) != 6:
            return False, "Face centers must each have a unique color."
        for color in range(6):
            if counts[color] != 9:
                return False, f"{COLOR_NAMES[color]}: {counts[color]}/9 stickers (needs 9)."
        return True, "Color counts and centers are valid."

    def normalize_state_for_solver(self):
        good, message = self.validate()
        if not good:
            raise ValueError(message)
        color_to_face = {self.state[face][1][1]: face for face in FACES}
        return "".join(color_to_face[self.state[face][r][c]] for face in FACES for r in range(3) for c in range(3))

    def get_state_string(self):
        return self.normalize_state_for_solver()

    def load_facelets(self, notation):
        """Import URFDLB order notation; centers are tied to their actual faces."""
        notation = "".join(notation.upper().split())
        if len(notation) != 54 or set(notation) - set(FACES):
            raise ValueError("Enter exactly 54 face letters: U, R, F, D, L, B.")
        if any(notation[idx * 9 + 4] != face for idx, face in enumerate(FACES)):
            raise ValueError("Center facelets must be U, R, F, D, L, B in order.")
        if any(notation.count(face) != 9 for face in FACES):
            raise ValueError("Each of the six face letters must occur exactly 9 times.")
        candidate = RubiksCube()
        for index, face in enumerate(FACES):
            sequence = notation[index * 9:(index + 1) * 9]
            candidate.set_face_from_list(face, [FACE_COLOR[letter] for letter in sequence])
        # Do not mutate the current cube until fast checks succeed.
        self.state = candidate.state

    def is_solved(self):
        return all(all(color == self.state[face][1][1] for row in self.state[face] for color in row) for face in FACES)
