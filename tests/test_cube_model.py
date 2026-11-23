"""Run with: python -m unittest discover -s tests -v (no GUI needed)."""

import random
import unittest
from collections import Counter

from cube_model import (
    COLOR_NAMES, FACE_BASIS, FACE_COLOR, FACES, RubiksCube,
    dot, inverse_move, slot_from_geometry, sticker_position,
)
from solver import solve_cube, kociemba


class CubeModelTests(unittest.TestCase):
    def setUp(self):
        self.cube = RubiksCube()

    def test_solved_state_and_notation(self):
        self.assertTrue(self.cube.is_solved())
        self.assertEqual(self.cube.get_state_string(), "".join(f * 9 for f in FACES))
        self.assertEqual(self.cube.validate()[0], True)

    def test_oriented_faces_have_orthogonal_bases(self):
        for face, (normal, right, up) in FACE_BASIS.items():
            self.assertEqual(dot(normal, right), 0, face)
            self.assertEqual(dot(normal, up), 0, face)
            self.assertEqual(dot(up, right), 0, face)
            self.assertEqual(sum(c * c for c in normal), 1, face)

    def test_sticker_coordinate_roundtrip(self):
        ids = set()
        for face in FACES:
            normal = FACE_BASIS[face][0]
            for r in range(3):
                for c in range(3):
                    pos = sticker_position(face, r, c)
                    self.assertEqual((face, r, c), slot_from_geometry(pos, normal))
                    ids.add((pos, normal))
        self.assertEqual(len(ids), 54)

    def test_each_move_and_inverse(self):
        for face in FACES:
            for suffix in ("", "'", "2"):
                with self.subTest(face=face, suffix=suffix):
                    move = face + suffix
                    cube = RubiksCube()
                    cube.execute_move(move)
                    cube.execute_move(inverse_move(move))
                    self.assertTrue(cube.is_solved())

    def test_four_quarter_turns_restore_state(self):
        for face in FACES:
            cube = RubiksCube()
            cube.apply_moves([face] * 4)
            self.assertTrue(cube.is_solved())

    def test_all_moves_preserve_complete_cubies(self):
        # A physically legal twist must preserve the multiset of 27 cubies,
        # not merely six balanced face colors.
        def multiset(cube):
            cubies = {}
            for f in FACES:
                for r in range(3):
                    for c in range(3):
                        location = sticker_position(f, r, c)
                        cubies.setdefault(location, []).append(cube.state[f][r][c])
            return Counter(tuple(sorted(colors)) for colors in cubies.values())

        expected = multiset(RubiksCube())
        for seed in range(35):
            cube = RubiksCube()
            cube.scramble(85, rng=random.Random(seed))
            self.assertEqual(multiset(cube), expected)
            self.assertEqual(cube.validate()[0], True)

    def test_deterministic_scrambles_and_no_repeated_axis(self):
        a, b = RubiksCube(), RubiksCube()
        ma = a.scramble(50, rng=random.Random(18))
        mb = b.scramble(50, rng=random.Random(18))
        self.assertEqual(ma, mb)
        self.assertEqual(a.snapshot(), b.snapshot())
        axis = dict(zip("UDRLFB", "001122"))
        self.assertTrue(all(axis[x[0]] != axis[y[0]] for x, y in zip(ma, ma[1:])))

    def test_manual_paint_and_center_protection(self):
        with self.assertRaises(ValueError):
            self.cube.set_sticker("U", 1, 1, 2)
        self.cube.set_sticker("U", 0, 0, 2)
        self.assertFalse(self.cube.validate()[0])
        self.assertIn(COLOR_NAMES[0], self.cube.validate()[1])

    def test_undo_snapshot_is_independent(self):
        before = self.cube.snapshot()
        self.cube.execute_move("R")
        self.cube.restore(before)
        self.assertTrue(self.cube.is_solved())
        before["U"][0][0] = 3
        self.assertTrue(self.cube.is_solved())

    def test_import_export_roundtrip(self):
        self.cube.scramble(20, rng=random.Random(4))
        encoded = self.cube.normalize_state_for_solver()
        imported = RubiksCube()
        imported.load_facelets(encoded)
        self.assertEqual(self.cube.snapshot(), imported.snapshot())
        self.assertEqual(encoded, imported.get_state_string())

    def test_import_atomic_invalid(self):
        before = self.cube.snapshot()
        for invalid in ("U" * 54, "x" * 54, "", "U" * 53 + "B"):
            with self.subTest(invalid=invalid[:10]):
                with self.assertRaises(ValueError):
                    self.cube.load_facelets(invalid)
                self.assertEqual(self.cube.snapshot(), before)

    def test_invalid_moves_raise(self):
        for invalid in ("X", "u", "F3", "", "U''", " U"):
            with self.assertRaises(ValueError):
                self.cube.execute_move(invalid)

    def test_solver_on_solved_and_error_handling(self):
        solution, error = solve_cube(self.cube)
        self.assertEqual(solution, [])
        self.assertIsNone(error)
        self.cube.execute_move("R")
        solution, error = solve_cube(self.cube)
        if kociemba is None:
            self.assertIsNone(solution)
            self.assertIn("pip install", error)
        else:
            self.assertIsNone(error)
            self.cube.apply_moves(solution)
            self.assertTrue(self.cube.is_solved())


if __name__ == "__main__":
    unittest.main()
