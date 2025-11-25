import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Matches: 0=White, 1=Yellow, 2=Red, 3=Orange, 4=Green, 5=Blue
COLORS_GL = [
    (1, 1, 1),   # 0 White
    (1, 1, 0),   # 1 Yellow
    (0.8, 0, 0), # 2 Red
    (1, 0.5, 0), # 3 Orange
    (0, 0.8, 0), # 4 Green
    (0, 0, 0.8)  # 5 Blue
]
BLACK = (0, 0, 0)

class CubeVisualizer:
    def __init__(self, width=800, height=600):
        pygame.init()
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        self.setup_gl(width, height)

    def setup_gl(self, width, height):
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLineWidth(2) # Thicker lines for edges

    def draw_cubie(self, x, y, z, face_colors):
        """
        face_colors: [U, D, F, B, L, R] specific colors for this cubie.
        None if that face is internal.
        """
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # Half-size
        s = 0.5
        
        # Geometry definition (Normal, Vertex Quad)
        surfaces = [
            # Up (y=1)
            ((0, 1, 0), [(-s, s, -s), (-s, s, s), (s, s, s), (s, s, -s)], face_colors[0]),
            # Down (y=-1)
            ((0, -1, 0), [(-s, -s, -s), (s, -s, -s), (s, -s, s), (-s, -s, s)], face_colors[1]),
            # Front (z=1)
            ((0, 0, 1), [(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)], face_colors[2]),
            # Back (z=-1)
            ((0, 0, -1), [(-s, -s, -s), (-s, s, -s), (s, s, -s), (s, -s, -s)], face_colors[3]),
            # Left (x=-1)
            ((-1, 0, 0), [(-s, -s, -s), (-s, -s, s), (-s, s, s), (-s, s, -s)], face_colors[4]),
            # Right (x=1)
            ((1, 0, 0), [(s, -s, -s), (s, s, -s), (s, s, s), (s, -s, s)], face_colors[5]),
        ]

        for normal, vertices, color_idx in surfaces:
            # 1. Draw Color Face
            if color_idx is not None:
                glColor3fv(COLORS_GL[color_idx])
            else:
                glColor3fv((0.1, 0.1, 0.1)) # Internal dark grey

            glBegin(GL_QUADS)
            glNormal3fv(normal)
            for v in vertices: glVertex3fv(v)
            glEnd()

            # 2. Draw Black Edge (Outline)
            glColor3fv(BLACK)
            glBegin(GL_LINE_LOOP)
            for v in vertices: glVertex3fv(v)
            glEnd()

        glPopMatrix()

    def render(self, cube, rot_x, rot_y, zoom):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Apply Camera
        glTranslatef(0.0, 0.0, zoom)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        # Iterate 3x3x3 grid (-1, 0, 1)
        # Map logical state to 3D position
        # Cube indices: 0,1,2. 3D Coords: -1, 0, 1
        # Mapping: 0 -> -1, 1 -> 0, 2 -> 1
        
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    # Physical coordinates
                    px, py, pz = (x-1)*1.05, (1-y)*1.05, (z-1)*1.05 
                    # Note: Y is inverted in GL usually (Up is positive), 
                    # but array index 0 is top. So y=0 -> py=1.

                    # Determine colors for this cubie
                    # Indices: U=0, D=1, F=2, B=3, L=4, R=5
                    cols = [None]*6
                    
                    # Logic to pick sticker color from cube.state
                    # y=0 is UP face. y=2 is DOWN face.
                    if y == 0: cols[0] = cube.state['U'][z][x] # U
                    if y == 2: cols[1] = cube.state['D'][z][x] # D
                    
                    # z=2 is FRONT face (index 2?). Wait, prompt mapping:
                    # Standard: Front is usually z+. 
                    # Let's assume Array structure: [row][col]
                    if z == 2: cols[2] = cube.state['F'][y][x] # F
                    if z == 0: cols[3] = cube.state['B'][y][2-x] # B (inverted x?)
                    
                    if x == 0: cols[4] = cube.state['L'][y][2-z] # L
                    if x == 2: cols[5] = cube.state['R'][y][z] # R
                    
                    # (Note: Exact [y][x] mapping depends on your mental model of the array orientation
                    # vs 3D space. This is a best-effort mapping for visual consistency).

                    self.draw_cubie(px, py, pz, cols)

        pygame.display.flip()
