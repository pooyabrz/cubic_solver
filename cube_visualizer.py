"""Software-rendered 3-D Rubik's Cube for pygame (no OpenGL required)."""

from __future__ import annotations

import math
import pygame

from cube_model import FACES, FACE_BASIS

STICKER_COLORS = (
    (235, 243, 251),  # white
    (255, 207, 84),   # yellow
    (249, 94, 99),    # red
    (255, 155, 89),   # orange
    (65, 215, 168),  # green
    (90, 155, 255),  # blue
)


def add(v, right, horizontal, up, vertical, normal, outward):
    return tuple(
        v[i] + horizontal * right[i] + vertical * up[i] + outward * normal[i]
        for i in range(3)
    )


def adjust(color, scale):
    return tuple(max(0, min(255, int(c * scale))) for c in color)


def in_polygon(point, vertices):
    """Ray-crossing hit test for a projected quadrilateral."""
    px, py = point
    inside = False
    for i, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(i + 1) % len(vertices)]
        if (y1 > py) != (y2 > py):
            crossed = (x2 - x1) * (py - y1) / (y2 - y1) + x1
            if px < crossed:
                inside = not inside
    return inside


class CubeVisualizer:
    def __init__(self):
        self.polygons = []  # (points, face, row, column); last drawn is foremost

    @staticmethod
    def transform(v, pitch, yaw):
        yaw_r = math.radians(yaw)
        pitch_r = math.radians(pitch)
        x, y, z = v
        x1 = x * math.cos(yaw_r) + z * math.sin(yaw_r)
        z1 = -x * math.sin(yaw_r) + z * math.cos(yaw_r)
        y2 = y * math.cos(pitch_r) - z1 * math.sin(pitch_r)
        z2 = y * math.sin(pitch_r) + z1 * math.cos(pitch_r)
        return x1, y2, z2

    def render(self, surface, cube, center, pitch, yaw, zoom, hover=None, paint_mode=False):
        cx, cy = center
        scale = 115 * zoom
        self.polygons = []

        def project(v):
            x, y, z = self.transform(v, pitch, yaw)
            perspective = 6.8 / (6.8 - z * 0.31)
            return (round(cx + x * scale * perspective),
                    round(cy - y * scale * perspective))

        faces = []
        for face in FACES:
            normal, right, up = FACE_BASIS[face]
            nz = self.transform(normal, pitch, yaw)[2]
            if nz > 0.025:
                faces.append((nz, face, normal, right, up))
        faces.sort(key=lambda item: item[0])

        for nz, face, normal, right, up in faces:
            origin = (0.0, 0.0, 0.0)
            board = [
                project(add(origin, right, hor, up, ver, normal, 1.49))
                for hor, ver in ((-1.49, -1.49), (1.49, -1.49), (1.49, 1.49), (-1.49, 1.49))
            ]
            pygame.draw.polygon(surface, (16, 25, 40), board)
            pygame.draw.polygon(surface, (51, 68, 88), board, 3)
            face_shade = 0.72 + 0.28 * min(1, nz)

            for row in range(3):
                for column in range(3):
                    # Sticker positions derive from the exact SAME basis as the
                    # cube's move permutations and Kociemba serialization.
                    right_pos, up_pos = column - 1, 1 - row
                    points = [
                        project(add(origin, right, right_pos + hor,
                                    up, up_pos + ver, normal, 1.51))
                        for hor, ver in ((-0.454, -0.454), (0.454, -0.454),
                                         (0.454, 0.454), (-0.454, 0.454))
                    ]
                    idx = cube.state[face][row][column]
                    color = STICKER_COLORS[idx]
                    pygame.draw.polygon(surface, (8, 17, 28), points)
                    pygame.draw.polygon(surface, adjust(color, face_shade), points)
                    pygame.draw.lines(surface, adjust(color, min(1.13, face_shade + 0.24)),
                                      False, points[2:4], 2)
                    pygame.draw.polygon(surface, (30, 40, 56), points, 2)
                    self.polygons.append((points, face, row, column))

        if paint_mode and hover is not None:
            sticker = self.hit_test(hover)
            if sticker:
                face, row, column = sticker
                if (row, column) != (1, 1):
                    points = next((poly for poly, f, r, c in reversed(self.polygons)
                                   if (f, r, c) == sticker), None)
                    if points:
                        pygame.draw.polygon(surface, (240, 250, 255), points, 4)
        return len(faces)

    def hit_test(self, position):
        for points, face, row, col in reversed(self.polygons):
            if in_polygon(position, points):
                return face, row, col
        return None
