"""CUBIQ Studio: a mouse-first Rubik's cube simulator and solver.

Run `python main.py`. Uses only pygame for rendering and the optional
Kociemba package for solving; no OpenGL context or separate UI toolkit.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import pygame

from cube_model import FACES, COLOR_NAMES, RubiksCube, inverse_move
from cube_visualizer import CubeVisualizer, STICKER_COLORS
from solver import solve_cube, kociemba

VW, VH = 1440, 900
DEFAULT_SIZE = (1440, 900)
STATE_FILE = Path.home() / ".cubiq-studio" / "session.json"

BG = (9, 15, 26)
CARD = (20, 31, 47)
CARD_HOVER = (30, 44, 64)
CARD_ALT = (25, 38, 55)
STROKE = (45, 65, 84)
MUTED = (140, 162, 181)
TEXT = (234, 242, 248)
TEAL = (79, 226, 196)
TEAL_DARK = (26, 74, 75)
AMBER = (255, 191, 105)
RED = (251, 119, 124)


def blend(a, b, ratio):
    return tuple(round(x * (1 - ratio) + y * ratio) for x, y in zip(a, b))


def rounded(surface, rect, color, radius=16, border=None, border_width=1):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, border_width, border_radius=radius)


class RubiksCubeApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CUBIQ  •  Rubik's Cube Studio")
        self.screen = pygame.display.set_mode(DEFAULT_SIZE, pygame.RESIZABLE)
        self.canvas = pygame.Surface((VW, VH))
        self.background = self.make_background()
        self.fonts = {
            size: pygame.font.SysFont("Segoe UI,Arial,DejaVu Sans", size)
            for size in (12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 34, 42)
        }
        self.bold_fonts = {
            size: pygame.font.SysFont("Segoe UI,Arial,DejaVu Sans", size, bold=True)
            for size in self.fonts
        }
        self.text_cache = {}
        self.cube = RubiksCube()
        self.visualizer = CubeVisualizer()
        self.running = True
        self.pitch, self.yaw, self.zoom = 28.0, -34.0, 1.0
        self.paint_mode = False
        self.selected_color = 2
        self.solution = []
        self.index = 0
        self.playing = False
        self.speed = 0.44  # seconds between moves
        self.last_step = time.monotonic()
        self.plan_scroll = 0
        self.undo_stack = []
        self.redo_stack = []
        self.modal = None  # 'help', 'notation'
        self.notation_text = ""
        self.toast = "Ready. Scramble the cube or paint your own stickers."
        self.toast_kind = "info"
        self.toast_until = time.monotonic() + 10
        self.hovered = None
        self.hotspots = []
        self.mouse = (-200, -200)
        self.dragging = False
        self.drag_moved = False
        self.drag_button = 0
        self.drag_last = (0, 0)
        self.drag_start = (0, 0)
        self.last_scramble = []
        self.last_cursor = None
        self._scrap_available = False
        try:
            pygame.scrap.init()
            self._scrap_available = True
        except (pygame.error, AttributeError):
            pass

    @staticmethod
    def make_background():
        bg = pygame.Surface((VW, VH))
        for y in range(VH):
            t = y / (VH - 1)
            pygame.draw.line(bg, blend((15, 25, 40), BG, t), (0, y), (VW, y))
        # Ambient decorative glow, made once so the main loop stays lightweight.
        halo = pygame.Surface((VW, VH), pygame.SRCALPHA)
        for rad in range(270, 20, -9):
            alpha = max(0, round(8 * (1 - rad / 300)))
            pygame.draw.circle(halo, (21, 120, 126, alpha), (460, 270), rad)
        bg.blit(halo, (0, 0))
        return bg

    def label(self, value, x, y, size=16, color=TEXT, align="topleft", bold=False):
        font = self.bold_fonts[size] if bold else self.fonts[size]
        value = str(value)
        key = (value, size, bold, color)
        surface = self.text_cache.get(key)
        if surface is None:
            if len(self.text_cache) >= 2048:
                self.text_cache.clear()
            surface = font.render(value, True, color)
            self.text_cache[key] = surface
        rect = surface.get_rect(**{align: (x, y)})
        self.canvas.blit(surface, rect)
        return rect

    def register(self, rect, callback, tooltip="", force=False, enabled=True):
        if self.modal and not force:
            return
        self.hotspots.append((pygame.Rect(rect), callback, tooltip, enabled))

    def button(self, rect, caption, callback, tooltip="", variant="subtle", size=16,
               force=False, enabled=True, leading=None):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(self.mouse) and enabled
        if variant == "primary":
            bg_color = (97, 238, 210) if hover else TEAL
            foreground = (9, 35, 42)
            border = None
        elif variant == "danger":
            bg_color = (94, 45, 59) if hover else (62, 37, 49)
            foreground = (255, 200, 201)
            border = (108, 56, 69)
        elif variant == "selected":
            bg_color = TEAL_DARK if not hover else (39, 98, 94)
            foreground = (178, 255, 236)
            border = (57, 158, 143)
        else:
            bg_color = CARD_HOVER if hover else CARD_ALT
            foreground = TEXT
            border = STROKE
        if not enabled:
            bg_color = (21, 31, 43)
            foreground = (95, 111, 126)
            border = (35, 48, 63)
        rounded(self.canvas, rect, bg_color, 12, border)
        if leading is not None:
            pygame.draw.circle(self.canvas, leading, (rect.x + 21, rect.centery), 6)
            self.label(caption, rect.centerx + 7, rect.centery, size, foreground, "center")
        else:
            self.label(caption, *rect.center, size, foreground, "center")
        self.register(rect, callback, tooltip, force, enabled)

    def card(self, rect, dark=False):
        rounded(self.canvas, rect, (16, 27, 42) if dark else CARD, 21, (42, 59, 77))

    def notify(self, text, kind="info"):
        self.toast, self.toast_kind = text, kind
        self.toast_until = time.monotonic() + 7.0

    def checkpoint(self):
        self.undo_stack.append(self.cube.snapshot())
        if len(self.undo_stack) > 120:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def clear_solution(self):
        self.playing = False
        self.solution = []
        self.index = 0
        self.plan_scroll = 0

    def turn(self, move):
        self.checkpoint()
        self.clear_solution()
        self.cube.execute_move(move)
        self.notify(f"Turned {move}. Use Undo to reverse it.")

    def scramble(self):
        self.checkpoint()
        self.clear_solution()
        self.last_scramble = self.cube.scramble(25)
        self.notify("Scrambled with 25 legal turns. Click Solve to find the route.", "success")

    def reset(self):
        if self.cube.is_solved():
            self.notify("Already solved.")
            return
        self.checkpoint()
        self.clear_solution()
        self.cube.reset()
        self.notify("Cube reset. Your previous state can be restored with Undo.", "success")

    def undo(self):
        if not self.undo_stack:
            self.notify("Nothing to undo.")
            return
        self.playing = False
        self.redo_stack.append(self.cube.snapshot())
        self.cube.restore(self.undo_stack.pop())
        self.clear_solution()
        self.notify("Last change undone.")

    def redo(self):
        if not self.redo_stack:
            self.notify("Nothing to redo.")
            return
        self.playing = False
        self.undo_stack.append(self.cube.snapshot())
        self.cube.restore(self.redo_stack.pop())
        self.clear_solution()
        self.notify("Change restored.")

    def paint(self, sticker):
        if not self.paint_mode:
            self.notify("Select a palette color to enable Paint mode.")
            return
        face, row, col = sticker
        if (row, col) == (1, 1):
            self.notify("Center stickers are fixed on a physical 3x3 cube.")
            return
        if self.cube.state[face][row][col] == self.selected_color:
            return
        self.checkpoint()
        self.clear_solution()
        self.cube.set_sticker(face, row, col, self.selected_color)
        self.notify(f"Painted {face} sticker ({row + 1}, {col + 1}) {COLOR_NAMES[self.selected_color]}.")

    def pick_color(self, color):
        self.selected_color = color
        self.paint_mode = True
        self.notify(f"Paint mode enabled. Click a sticker to apply {COLOR_NAMES[color]}.")

    def plan(self):
        if self.playing:
            self.playing = False
        solution, error = solve_cube(self.cube)
        if error:
            self.notify(error, "error")
            return False
        self.solution = solution
        self.index = 0
        self.plan_scroll = 0
        if not solution:
            self.notify("The cube is already solved!", "success")
        else:
            self.notify(f"Solution ready: {len(solution)} moves. Press Play or Next.", "success")
        return bool(solution)

    def next_step(self):
        self.playing = False
        if not self.solution and not self.plan():
            return
        if self.index >= len(self.solution):
            self.notify("All solution steps are complete.", "success")
            return
        move = self.solution[self.index]
        self.cube.execute_move(move)
        self.index += 1
        self.auto_scroll_plan()
        if self.index == len(self.solution):
            self.notify("Solution complete. Cube solved!", "success")

    def previous_step(self):
        self.playing = False
        if not self.solution or self.index == 0:
            self.notify("Already at the beginning of the solution.")
            return
        self.index -= 1
        self.cube.execute_move(inverse_move(self.solution[self.index]))
        self.auto_scroll_plan()

    def auto_scroll_plan(self):
        if self.index > self.plan_scroll + 6:
            self.plan_scroll = self.index - 6
        if self.index < self.plan_scroll:
            self.plan_scroll = self.index

    def jump_to_step(self, count):
        self.playing = False
        if not self.solution:
            return
        while self.index < count:
            self.cube.execute_move(self.solution[self.index])
            self.index += 1
        while self.index > count:
            self.index -= 1
            self.cube.execute_move(inverse_move(self.solution[self.index]))
        self.auto_scroll_plan()

    def toggle_play(self):
        if self.playing:
            self.playing = False
            self.notify("Playback paused. Use Next or Back to inspect moves.")
            return
        if not self.solution and not self.plan():
            return
        if self.index >= len(self.solution):
            self.notify("Solution is complete. Press Solve to plan again.")
            return
        self.playing = True
        self.last_step = time.monotonic()  # first step not skipped
        self.notify("Playing solution. Press Pause or Space to stop.")

    def update(self):
        if self.playing and time.monotonic() - self.last_step >= self.speed:
            self.last_step = time.monotonic()
            if self.index < len(self.solution):
                self.cube.execute_move(self.solution[self.index])
                self.index += 1
                self.auto_scroll_plan()
            if self.index >= len(self.solution):
                self.playing = False
                self.notify("Solved! All steps applied.", "success")

    def change_speed(self, delta):
        self.speed = round(min(1.3, max(0.12, self.speed + delta)), 2)
        self.notify(f"Playback delay: {self.speed:.2f} seconds per move.")

    def toggle_paint(self):
        self.paint_mode = not self.paint_mode
        self.notify("Paint mode ON: click stickers to recolor." if self.paint_mode
                    else "Paint mode OFF: rotate the cube with the mouse.")

    def open_modal(self, name):
        self.playing = False
        self.modal = name
        if name == "notation":
            try:
                self.notation_text = self.cube.normalize_state_for_solver()
            except ValueError:
                self.notation_text = ""
            pygame.key.start_text_input()

    def close_modal(self):
        self.modal = None
        pygame.key.stop_text_input()

    def clipboard_copy(self):
        if not self._scrap_available:
            self.notify("Clipboard unavailable on this system. You can select and copy the notation manually.", "error")
            return
        try:
            pygame.scrap.put(pygame.SCRAP_TEXT, self.notation_text.encode("utf-8") + b"\x00")
            self.notify("54-character cube state copied to clipboard.", "success")
        except (pygame.error, AttributeError):
            self.notify("Clipboard copy is not supported in this session.", "error")

    def clipboard_paste(self):
        if not self._scrap_available:
            self.notify("Clipboard unavailable. Type the notation in the field.", "error")
            return
        try:
            content = pygame.scrap.get(pygame.SCRAP_TEXT)
            if content:
                self.notation_text = content.decode("utf-8", errors="ignore").replace("\x00", "").strip().upper()[:200]
        except (pygame.error, AttributeError):
            self.notify("Cannot paste from the system clipboard.", "error")

    def import_notation(self):
        old = self.cube.snapshot()
        try:
            self.cube.load_facelets(self.notation_text)
            if kociemba is not None and not self.cube.is_solved():
                # Do not accept a color-balanced but physically impossible cube.
                kociemba.solve(self.cube.normalize_state_for_solver())
        except Exception as exc:
            self.cube.restore(old)
            self.notify(f"Import failed: {exc}", "error")
            return
        self.undo_stack.append(old)
        self.redo_stack.clear()
        self.clear_solution()
        self.close_modal()
        self.notify("Cube state imported successfully.", "success")

    def save_session(self):
        payload = {
            "version": 1, "faces": self.cube.state,
            "camera": {"pitch": self.pitch, "yaw": self.yaw, "zoom": self.zoom},
            "speed": self.speed,
        }
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.notify(f"Session saved: {STATE_FILE}", "success")
        except OSError as exc:
            self.notify(f"Cannot save session: {exc}", "error")

    def load_session(self):
        try:
            payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            candidate = RubiksCube()
            for f in FACES:
                values = payload["faces"][f]
                candidate.set_face_from_list(f, [color for row in values for color in row])
            if len({candidate.state[f][1][1] for f in FACES}) != 6:
                raise ValueError("Center colors must be unique.")
            cam = payload.get("camera", {})
            pitch = max(-85, min(85, float(cam.get("pitch", 28))))
            yaw = float(cam.get("yaw", -34))
            zoom = max(0.55, min(1.5, float(cam.get("zoom", 1))))
            speed = max(0.12, min(1.3, float(payload.get("speed", 0.44))))
            if not all(math.isfinite(value) for value in (pitch, yaw, zoom, speed)):
                raise ValueError("Saved camera or speed values must be finite numbers.")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.notify(f"Cannot load session: {exc}", "error")
            return
        self.checkpoint()
        self.cube.restore(candidate.snapshot())
        self.pitch, self.yaw, self.zoom, self.speed = pitch, yaw, zoom, speed
        self.clear_solution()
        self.close_modal()
        self.notify("Saved session restored. Undo is available.", "success")

    def reset_view(self):
        self.pitch, self.yaw, self.zoom = 28.0, -34.0, 1.0
        self.notify("Camera returned to the default angle.")

    def virtual_point(self, xy):
        sw, sh = self.screen.get_size()
        factor = min(sw / VW, sh / VH)
        offset_x, offset_y = (sw - VW * factor) / 2, (sh - VH * factor) / 2
        return (int((xy[0] - offset_x) / factor), int((xy[1] - offset_y) / factor))

    def over_cube(self, point):
        return pygame.Rect(37, 174, 817, 518).collidepoint(point)

    def find_hotspot(self, point):
        for rect, action, tooltip, enabled in reversed(self.hotspots):
            if rect.collidepoint(point):
                return rect, action, tooltip, enabled
        return None

    def on_click(self, pos):
        spot = self.find_hotspot(pos)
        if spot:
            _, action, _, enabled = spot
            if enabled:
                action()
            return
        if not self.modal and self.over_cube(pos):
            sticker = self.visualizer.hit_test(pos)
            if sticker and self.paint_mode:
                self.paint(sticker)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((max(850, event.w), max(540, event.h)), pygame.RESIZABLE)
            return
        if event.type == pygame.MOUSEMOTION:
            self.mouse = self.virtual_point(event.pos)
            if self.dragging:
                dx = self.mouse[0] - self.drag_last[0]
                dy = self.mouse[1] - self.drag_last[1]
                if abs(self.mouse[0] - self.drag_start[0]) + abs(self.mouse[1] - self.drag_start[1]) > 6:
                    self.drag_moved = True
                if self.drag_moved:
                    self.yaw += dx * 0.46
                    self.pitch = max(-85, min(85, self.pitch + dy * 0.46))
                self.drag_last = self.mouse
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            point = self.virtual_point(event.pos)
            self.mouse = point
            if event.button in (1, 3) and not self.modal and self.over_cube(point):
                self.dragging = True
                self.drag_button = event.button
                self.drag_moved = False
                self.drag_start = point
                self.drag_last = point
            elif event.button == 1:
                self.dragging = False
            return
        if event.type == pygame.MOUSEBUTTONUP:
            point = self.virtual_point(event.pos)
            self.mouse = point
            if self.dragging and event.button == self.drag_button:
                if event.button == 1 and not self.drag_moved:
                    self.on_click(point)
                self.dragging = False
            elif event.button == 1:
                self.on_click(point)
            return
        if event.type == pygame.MOUSEWHEEL:
            if self.modal:
                return
            if self.over_cube(self.mouse):
                self.zoom = max(0.55, min(1.5, self.zoom * (1 + event.y * 0.085)))
            return
        if event.type == pygame.TEXTINPUT and self.modal == "notation":
            incoming = "".join(ch for ch in event.text.upper() if ch in "URFDLB \n")
            self.notation_text = (self.notation_text + incoming)[:200]
            return
        if event.type != pygame.KEYDOWN:
            return
        mods = event.mod
        ctrl = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)
        if self.modal:
            if event.key == pygame.K_ESCAPE:
                self.close_modal()
            elif self.modal == "notation":
                if ctrl and event.key == pygame.K_v:
                    self.clipboard_paste()
                elif ctrl and event.key == pygame.K_c:
                    self.clipboard_copy()
                elif event.key == pygame.K_BACKSPACE:
                    self.notation_text = self.notation_text[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.import_notation()
            return
        if ctrl:
            if event.key == pygame.K_z:
                self.undo()
            elif event.key == pygame.K_y:
                self.redo()
            elif event.key == pygame.K_s:
                self.save_session()
            elif event.key == pygame.K_o:
                self.load_session()
            elif event.key == pygame.K_i:
                self.open_modal("notation")
            elif event.key == pygame.K_q:
                self.running = False
            return
        if event.key == pygame.K_ESCAPE:
            self.open_modal("help")
        elif event.key in (pygame.K_h, pygame.K_F1):
            self.open_modal("help")
        elif event.key == pygame.K_e:
            self.toggle_paint()
        elif event.key == pygame.K_s:
            self.scramble()
        elif event.key == pygame.K_x:
            self.reset()
        elif event.key == pygame.K_SPACE:
            self.toggle_play()
        elif event.key == pygame.K_n:
            self.next_step()
        elif event.key == pygame.K_p:
            self.previous_step()
        elif event.key == pygame.K_LEFT:
            self.yaw -= 7
        elif event.key == pygame.K_RIGHT:
            self.yaw += 7
        elif event.key == pygame.K_UP:
            self.pitch = max(-85, self.pitch - 7)
        elif event.key == pygame.K_DOWN:
            self.pitch = min(85, self.pitch + 7)
        else:
            letter = pygame.key.name(event.key).upper()
            if letter in FACES:
                self.turn(letter + ("'" if mods & pygame.KMOD_SHIFT else ""))

    def draw_header(self):
        # Custom abstract cube logomark.
        for dx, dy, color in ((0, 8, STICKER_COLORS[4]), (17, 0, STICKER_COLORS[5]),
                              (17, 19, STICKER_COLORS[2])):
            rounded(self.canvas, (31 + dx, 28 + dy, 22, 22), color, 5)
        self.label("CUBIQ", 93, 22, 34, TEXT, bold=True)
        self.label("RUBIK'S CUBE STUDIO", 96, 63, 13, MUTED)
        valid, _ = self.cube.validate()
        badge = ("SOLVED", TEAL) if valid and self.cube.is_solved() else (("COLORS OK", TEAL) if valid else ("CHECK COLORS", AMBER))
        badge_rect = pygame.Rect(720, 40, 153, 34)
        rounded(self.canvas, badge_rect, TEAL_DARK if valid else (80, 58, 42), 17)
        pygame.draw.circle(self.canvas, badge[1], (740, 57), 5)
        self.label(badge[0], 753, 48, 14, badge[1], bold=True)
        self.button((930, 31, 134, 49), "Reset view", self.reset_view,
                    "Restore default camera rotation and zoom")
        self.button((1078, 31, 150, 49), "Import / Export", lambda: self.open_modal("notation"),
                    "Load or copy a standard 54-character cube state")
        self.button((1242, 31, 170, 49), "?  How to use", lambda: self.open_modal("help"),
                    "Mouse controls, keyboard shortcuts, color editing and solver help", variant="selected")

    def draw_hero(self):
        area = pygame.Rect(26, 113, 840, 609)
        self.card(area, dark=True)
        self.label("THE WORKSPACE", 52, 134, 14, TEAL, bold=True)
        self.label("Explore your cube in 3D", 52, 155, 23, TEXT, bold=True)
        self.label("LIVE VIEW", 729, 146, 13, MUTED)
        # Orbit rings and softly painted backboard.
        mid = (447, 419)
        for radius, alpha in ((267, 14), (225, 13), (173, 10)):
            overlay = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (81, 166, 171, alpha), (radius + 4, radius + 4), radius, 1)
            self.canvas.blit(overlay, (mid[0] - radius - 4, mid[1] - radius - 4))
        pygame.draw.ellipse(self.canvas, (13, 26, 38), (284, 629, 330, 21))
        hover = self.mouse if self.over_cube(self.mouse) else None
        self.visualizer.render(self.canvas, self.cube, mid, self.pitch, self.yaw,
                               self.zoom, hover=hover, paint_mode=self.paint_mode)
        # Viewport zoom controls.
        self.button((777, 215, 51, 45), "+", lambda: self.zoom_by(1.12), "Zoom in", size=23)
        self.button((777, 268, 51, 45), "-", lambda: self.zoom_by(1 / 1.12), "Zoom out", size=23)
        if self.paint_mode:
            rounded(self.canvas, (50, 628, 164, 30), TEAL_DARK, 14)
            self.label("PAINT MODE ACTIVE", 132, 643, 13, TEAL, "center", bold=True)
        rounded(self.canvas, (47, 667, 797, 38), (26, 42, 60), 11)
        spot = self.find_hotspot(self.mouse)
        tooltip = spot[2] if spot and spot[2] else ""
        if not tooltip and self.paint_mode and hover and self.visualizer.hit_test(hover):
            tooltip = "Click this sticker to paint; center stickers are fixed"
        tip = tooltip or "DRAG to rotate     •     SCROLL to zoom     •     CLICK a sticker while painting"
        self.label(tip[:100], 65, 677, 15, (173, 213, 219))

    def zoom_by(self, value):
        self.zoom = max(0.55, min(1.5, self.zoom * value))

    def draw_manual(self):
        self.card((26, 735, 840, 143))
        self.label("TURN A FACE", 52, 747, 16, TEXT, bold=True)
        self.label("Click any move. Hold Shift with a face letter for reverse turns.", 188, 748, 13, MUTED)
        short_faces = ("U", "R", "F", "D", "L", "B")
        gap, bw, left = 9, 119, 52
        for i, face in enumerate(short_faces):
            self.button((left + i * (bw + gap), 779, bw, 40), face,
                        lambda f=face: self.turn(f), f"Turn {face} clockwise")
            self.button((left + i * (bw + gap), 828, bw, 37), face + "'",
                        lambda f=face: self.turn(f + "'"), f"Turn {face} counterclockwise", size=15)

    def draw_actions(self):
        self.card((887, 113, 527, 179))
        self.label("QUICK ACTIONS", 909, 130, 17, TEXT, bold=True)
        self.label("Everything is clickable", 1369, 133, 13, MUTED, "topright")
        x_values = (909, 1075, 1241)
        w = 151
        self.button((x_values[0], 171, w, 44), "Scramble", self.scramble,
                    "Generate a 25-turn random scramble", variant="selected")
        self.button((x_values[1], 171, w, 44), "Reset", self.reset,
                    "Return to solved; Ctrl+Z restores your previous state")
        self.button((x_values[2], 171, w, 44), "Find solution", self.plan,
                    "Calculate a Kociemba solution without changing the cube", variant="primary")
        self.button((x_values[0], 227, w, 44), "Pause" if self.playing else "Play / Resume",
                    self.toggle_play, "Animate the solution; Space toggles playback")
        self.button((x_values[1], 227, w, 44), "Undo", self.undo,
                    "Undo the last manual change (Ctrl+Z)", enabled=bool(self.undo_stack))
        self.button((x_values[2], 227, w, 44), "Redo", self.redo,
                    "Redo an undone change (Ctrl+Y)", enabled=bool(self.redo_stack))

    def draw_solution(self):
        self.card((887, 305, 527, 190))
        self.label("SOLUTION ROADMAP", 909, 320, 17, TEXT, bold=True)
        if self.solution:
            progress = self.index / len(self.solution)
            self.label(f"{self.index} / {len(self.solution)} moves", 1392, 323, 14, TEAL, "topright")
        else:
            progress = 0
            self.label("Not calculated", 1392, 323, 14, MUTED, "topright")
        rounded(self.canvas, (909, 351, 483, 7), (45, 64, 78), 4)
        if progress:
            rounded(self.canvas, (909, 351, max(7, int(483 * progress)), 7), TEAL, 4)
        if not self.solution:
            self.label("Find a solution, then inspect each move or play automatically.", 909, 376, 14, MUTED)
            if self.last_scramble:
                summary = " ".join(self.last_scramble[:12]) + "  ..."
                self.label("LAST SCRAMBLE  " + summary, 909, 398, 13, (139, 191, 184))
        else:
            for j in range(self.plan_scroll, min(len(self.solution), self.plan_scroll + 8)):
                place = j - self.plan_scroll
                rect = pygame.Rect(909 + place * 61, 372, 54, 40)
                color = TEAL_DARK if j < self.index else (66, 81, 101) if j == self.index else (28, 44, 61)
                rounded(self.canvas, rect, color, 10, (58, 93, 97) if j < self.index else STROKE)
                self.label(self.solution[j], *rect.center, 16, TEAL if j < self.index else TEXT, "center")
                self.register(rect, lambda n=j: self.jump_to_step(n + 1),
                              f"Jump to the state after step {j + 1}: {self.solution[j]}")
        self.button((909, 438, 145, 42), "< Back", self.previous_step,
                    "Rewind one planned move (P)", enabled=self.index > 0)
        self.button((1063, 438, 145, 42), "Next >", self.next_step,
                    "Perform the next move (N)")
        self.button((1220, 438, 36, 42), "-", lambda: self.change_speed(+0.08),
                    "Slow down animation")
        self.button((1356, 438, 36, 42), "+", lambda: self.change_speed(-0.08),
                    "Speed up animation")
        self.label(f"{self.speed:.2f}s", 1305, 446, 16, TEXT, "midtop")

    def net_face(self, face, x, y):
        self.label(face, x + 30, y - 15, 13, MUTED, "center", bold=True)
        rounded(self.canvas, (x - 4, y - 4, 68, 68), (38, 56, 70), 7)
        for row in range(3):
            for col in range(3):
                rect = pygame.Rect(x + col * 20, y + row * 20, 19, 19)
                color = STICKER_COLORS[self.cube.state[face][row][col]]
                pygame.draw.rect(self.canvas, color, rect, border_radius=3)
                if (row, col) == (1, 1):
                    pygame.draw.rect(self.canvas, (27, 42, 58), rect, 2, border_radius=3)
                    pygame.draw.circle(self.canvas, (29, 40, 54), rect.center, 2)
                if self.paint_mode and rect.collidepoint(self.mouse) and (row, col) != (1, 1):
                    pygame.draw.rect(self.canvas, TEAL, rect.inflate(4, 4), 2, border_radius=4)
                tip = "Center is fixed" if (row, col) == (1, 1) else f"Paint {face} row {row + 1}, column {col + 1}"
                self.register(rect, lambda f=face, r=row, c=col: self.paint((f, r, c)), tip)

    def draw_editor(self):
        self.card((887, 508, 527, 370))
        self.label("STICKER EDITOR", 909, 521, 17, TEXT, bold=True)
        mode = "Paint: ON" if self.paint_mode else "Paint: OFF"
        self.button((1270, 518, 122, 35), mode, self.toggle_paint,
                    "Enable or disable coloring with the mouse (E)",
                    variant="selected" if self.paint_mode else "subtle", size=14)
        self.label("Choose a color, then click any non-center sticker.", 909, 554, 14, MUTED)
        # Unfolded net. All six sides stay available regardless of the 3D camera.
        base_x, spacing, sx = 1005, 76, 60
        self.net_face("U", base_x + spacing, 601)
        for i, f in enumerate(("L", "F", "R", "B")):
            self.net_face(f, base_x + i * spacing, 669)
        self.net_face("D", base_x + spacing, 737)
        for idx, color in enumerate(STICKER_COLORS):
            x, y = 1005 + idx * 62, 835
            active = idx == self.selected_color
            if active:
                pygame.draw.circle(self.canvas, TEAL, (x, y), 22, 3)
            pygame.draw.circle(self.canvas, color, (x, y), 15)
            pygame.draw.circle(self.canvas, (14, 25, 39), (x, y), 15, 2)
            area = pygame.Rect(x - 23, y - 23, 46, 46)
            self.register(area, lambda c=idx: self.pick_color(c),
                          f"Select {COLOR_NAMES[idx]}; enables Paint mode")
        valid, reason = self.cube.validate()
        if not valid:
            self.label(reason[:43], 909, 859, 12, AMBER)
        else:
            self.label("All colors balanced  •  Centers locked", 909, 859, 12, MUTED)

    def draw_tooltip(self):
        """Show a real hover tooltip for every on-screen control."""
        spot = self.find_hotspot(self.mouse)
        if not spot or not spot[2] or not spot[3]:
            return
        tooltip = spot[2]
        max_text_width = 414
        words = tooltip.split()
        rows = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if current and self.fonts[14].size(candidate)[0] > max_text_width:
                rows.append(current)
                current = word
            else:
                current = candidate
        if current:
            rows.append(current)
        rows = rows[:3]
        width = min(455, max(138, max((self.fonts[14].size(row)[0] for row in rows), default=120) + 28))
        height = 20 + 21 * len(rows)
        x = min(VW - width - 14, max(14, self.mouse[0] + 17))
        y = self.mouse[1] - height - 17
        if y < 12:
            y = min(VH - height - 14, self.mouse[1] + 22)
        rounded(self.canvas, (x, y, width, height), (8, 20, 32), 10, (72, 111, 120))
        for i, row in enumerate(rows):
            self.label(row, x + 14, y + 10 + i * 21, 14, (226, 241, 240))

    def draw_footer(self):
        if time.monotonic() < self.toast_until:
            color = RED if self.toast_kind == "error" else TEAL if self.toast_kind == "success" else MUTED
            pygame.draw.circle(self.canvas, color, (42, 894), 5)
            self.label(self.toast[:110], 55, 882, 13, color)
        else:
            self.label("F1 Help   •   Ctrl+S Save   •   Ctrl+O Restore   •   Ctrl+I Import/Export", 30, 882, 12, MUTED)

    def draw_help(self):
        # Modal's actions use force=True, while underlying hotspots are cleared.
        self.hotspots.clear()
        overlay = pygame.Surface((VW, VH), pygame.SRCALPHA)
        overlay.fill((3, 9, 18, 213))
        self.canvas.blit(overlay, (0, 0))
        rounded(self.canvas, (318, 120, 804, 675), (24, 37, 54), 25, (73, 103, 116), 2)
        self.label("WELCOME TO CUBIQ", 359, 151, 14, TEAL, bold=True)
        self.label("Everything you need, in one view", 359, 180, 34, TEXT, bold=True)
        self.label("You can use the app entirely with the mouse. Shortcuts are optional.", 359, 228, 17, MUTED)
        content = [
            ("01", "Move the camera", "Drag the 3D cube. Scroll to zoom, or use the + / - buttons."),
            ("02", "Turn the cube", "Click U, R, F, D, L, B buttons below the workspace; lower row is reverse."),
            ("03", "Enter your own colors", "Select a color and click stickers in the unfolded net or on the cube."),
            ("04", "Find a solution", "Choose Find solution, then Play, Next or Back. Click a move to jump."),
            ("05", "Keep your work", "Ctrl+S saves the session. Import / Export supports 54-letter notation."),
        ]
        y = 282
        for num, heading, detail in content:
            rounded(self.canvas, (358, y, 46, 43), TEAL_DARK, 11)
            self.label(num, 381, y + 21, 16, TEAL, "center", bold=True)
            self.label(heading, 422, y - 3, 20, TEXT, bold=True)
            self.label(detail, 422, y + 25, 15, MUTED)
            y += 76
        rounded(self.canvas, (358, 667, 724, 48), (30, 46, 63), 10)
        self.label("SHORTCUTS  S scramble   X reset   E paint   Space play   N/P steps", 375, 674, 15, TEXT)
        self.label("Face letter = clockwise   Shift + letter = reverse   Ctrl+Z/Y = undo/redo", 375, 695, 14, MUTED)
        self.button((885, 732, 195, 46), "Start exploring", self.close_modal,
                    "Close help (Esc)", variant="primary", force=True)
        self.button((1048, 136, 48, 39), "X", self.close_modal, "Close help", force=True)

    def draw_notation(self):
        self.hotspots.clear()
        overlay = pygame.Surface((VW, VH), pygame.SRCALPHA)
        overlay.fill((3, 9, 18, 214))
        self.canvas.blit(overlay, (0, 0))
        rounded(self.canvas, (278, 194, 884, 504), (23, 37, 55), 24, (74, 104, 117), 2)
        self.label("IMPORT / EXPORT", 310, 221, 15, TEAL, bold=True)
        self.label("Share a cube state", 310, 251, 34, TEXT, bold=True)
        self.label("Standard Singmaster facelet order: U → R → F → D → L → B (9 letters per face).", 311, 310, 16, MUTED)
        self.label("Example: UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB", 311, 343, 14, (176, 204, 216))
        text_rect = pygame.Rect(310, 381, 820, 57)
        rounded(self.canvas, text_rect, (11, 24, 38), 12, (66, 113, 116), 2)
        shown = self.notation_text[-67:]
        self.label(shown or "Type or paste the 54-character state here ...", 325, 397, 16,
                   TEXT if shown else MUTED)
        if int(time.monotonic() * 2) % 2:
            text_w = self.fonts[16].size(shown)[0]
            if text_w < 781:
                pygame.draw.line(self.canvas, TEAL, (326 + text_w, 391), (326 + text_w, 424), 1)
        length = len("".join(self.notation_text.split()))
        self.label(f"{length} / 54 characters", 1129, 448, 13,
                   TEAL if length == 54 else AMBER, "topright")
        if time.monotonic() < self.toast_until:
            feedback_color = RED if self.toast_kind == "error" else TEAL if self.toast_kind == "success" else MUTED
            self.label(self.toast[:88], 310, 450, 13, feedback_color)
        self.button((310, 481, 191, 47), "Import state", self.import_notation,
                    "Load the typed cube notation; validates colors and physical state", "primary", force=True)
        self.button((515, 481, 183, 47), "Copy to clipboard", self.clipboard_copy,
                    "Copy the notation currently shown", force=True)
        self.button((712, 481, 180, 47), "Paste clipboard", self.clipboard_paste,
                    "Paste a 54-character cube state", force=True)
        self.button((903, 481, 227, 47), "Use current state", self.use_current_notation,
                    "Populate the input with the cube's current state", force=True)
        pygame.draw.line(self.canvas, (67, 89, 105), (310, 553), (1130, 553), 1)
        self.label("LOCAL SESSION", 310, 575, 15, TEAL)
        self.label("Save or reopen your cube with camera angle and playback speed.", 310, 601, 15, MUTED)
        self.button((310, 641, 191, 40), "Save session", self.save_session,
                    "Save your cube to your home folder", force=True)
        self.button((514, 641, 191, 40), "Restore session", self.load_session,
                    "Load the most recently saved cube", force=True)
        self.button((992, 641, 138, 40), "Close", self.close_modal, "Close (Esc)", force=True)
        self.button((1080, 212, 49, 38), "X", self.close_modal, "Close dialog", force=True)

    def use_current_notation(self):
        try:
            self.notation_text = self.cube.normalize_state_for_solver()
            self.notify("Current cube state filled in.", "success")
        except ValueError as exc:
            self.notify(str(exc), "error")

    def draw(self):
        self.hotspots = []
        self.canvas.blit(self.background, (0, 0))
        self.draw_header()
        self.draw_hero()
        self.draw_manual()
        self.draw_actions()
        self.draw_solution()
        self.draw_editor()
        self.draw_footer()
        if not self.modal:
            self.draw_tooltip()
        if self.modal == "help":
            self.draw_help()
        elif self.modal == "notation":
            self.draw_notation()
        size = self.screen.get_size()
        factor = min(size[0] / VW, size[1] / VH)
        dw, dh = round(VW * factor), round(VH * factor)
        self.screen.fill((6, 12, 19))
        if (dw, dh) == (VW, VH):
            shown = self.canvas
        else:
            shown = pygame.transform.smoothscale(self.canvas, (dw, dh))
        self.screen.blit(shown, ((size[0] - dw) // 2, (size[1] - dh) // 2))
        pygame.display.flip()
        hit = self.find_hotspot(self.mouse)
        interactive = hit is not None and hit[3]
        if not self.modal and self.over_cube(self.mouse):
            interactive = True
        cursor = pygame.SYSTEM_CURSOR_HAND if interactive else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.last_cursor:
            try:
                pygame.mouse.set_cursor(cursor)
                self.last_cursor = cursor
            except pygame.error:
                pass

    def run(self):
        clock = pygame.time.Clock()
        try:
            self.draw()
            while self.running:
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update()
                self.draw()
                clock.tick(45)
        finally:
            pygame.quit()


if __name__ == "__main__":
    RubiksCubeApp().run()
