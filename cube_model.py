import numpy as np
import random

class RubiksCube:
    """
    0=White (U), 1=Yellow (D), 2=Red (F), 3=Orange (B), 4=Green (L), 5=Blue (R)
    """
    def __init__(self):
        self.reset()

    def reset(self):
        # Initialize standard solved state
        self.state = {
            'U': np.full((3, 3), 0, dtype=int),
            'D': np.full((3, 3), 1, dtype=int),
            'F': np.full((3, 3), 2, dtype=int),
            'B': np.full((3, 3), 3, dtype=int),
            'L': np.full((3, 3), 4, dtype=int),
            'R': np.full((3, 3), 5, dtype=int)
        }

    def rotate_face_cw(self, face):
        # numpy rot90 is CCW, so k=-1 is CW
        self.state[face] = np.rot90(self.state[face], -1)

    def rotate_face_ccw(self, face):
        self.state[face] = np.rot90(self.state[face], 1)

    # --- MOVE LOGIC ---
    # NOTE: We use .copy() to ensure we don't overwrite data while swapping

    def move_U(self):
        self.rotate_face_cw('U')
        # F -> L -> B -> R -> F (Top Row)
        temp = self.state['F'][0, :].copy()
        self.state['F'][0, :] = self.state['R'][0, :]
        self.state['R'][0, :] = self.state['B'][0, :]
        self.state['B'][0, :] = self.state['L'][0, :]
        self.state['L'][0, :] = temp

    def move_U_prime(self):
        self.rotate_face_ccw('U')
        # Reverse of U
        temp = self.state['F'][0, :].copy()
        self.state['F'][0, :] = self.state['L'][0, :]
        self.state['L'][0, :] = self.state['B'][0, :]
        self.state['B'][0, :] = self.state['R'][0, :]
        self.state['R'][0, :] = temp

    def move_D(self):
        self.rotate_face_cw('D')
        # F -> R -> B -> L -> F (Bottom Row)
        temp = self.state['F'][2, :].copy()
        self.state['F'][2, :] = self.state['L'][2, :]
        self.state['L'][2, :] = self.state['B'][2, :]
        self.state['B'][2, :] = self.state['R'][2, :]
        self.state['R'][2, :] = temp

    def move_D_prime(self):
        self.rotate_face_ccw('D')
        temp = self.state['F'][2, :].copy()
        self.state['F'][2, :] = self.state['R'][2, :]
        self.state['R'][2, :] = self.state['B'][2, :]
        self.state['B'][2, :] = self.state['L'][2, :]
        self.state['L'][2, :] = temp

    def move_F(self):
        self.rotate_face_cw('F')
        # Cycle: U(row2) -> R(col0) -> D(row0) -> L(col2) -> U(row2)
        # Clockwise rotation of Front face moves Up pieces to Right, Right to Down, etc.
        temp = self.state['U'][2, :].copy()
        self.state['U'][2, :] = self.state['L'][:, 2][::-1] # L col 2 (inverted order)
        self.state['L'][:, 2] = self.state['D'][0, :] 
        self.state['D'][0, :] = self.state['R'][:, 0][::-1] # R col 0 (inverted order)
        self.state['R'][:, 0] = temp

    def move_F_prime(self):
        self.rotate_face_ccw('F')
        temp = self.state['U'][2, :].copy()
        self.state['U'][2, :] = self.state['R'][:, 0]
        self.state['R'][:, 0] = self.state['D'][0, :][::-1]
        self.state['D'][0, :] = self.state['L'][:, 2]
        self.state['L'][:, 2] = temp[::-1]

    def move_B(self):
        self.rotate_face_cw('B')
        # Cycle: U(row0) -> L(col0) -> D(row2) -> R(col2)
        temp = self.state['U'][0, :].copy()
        self.state['U'][0, :] = self.state['R'][:, 2]
        self.state['R'][:, 2] = self.state['D'][2, :][::-1]
        self.state['D'][2, :] = self.state['L'][:, 0]
        self.state['L'][:, 0] = temp[::-1]

    def move_B_prime(self):
        self.rotate_face_ccw('B')
        temp = self.state['U'][0, :].copy()
        self.state['U'][0, :] = self.state['L'][:, 0][::-1]
        self.state['L'][:, 0] = self.state['D'][2, :]
        self.state['D'][2, :] = self.state['R'][:, 2][::-1]
        self.state['R'][:, 2] = temp

    def move_L(self):
        self.rotate_face_cw('L')
        # Cycle: U(col0) -> F(col0) -> D(col0) -> B(col2)
        temp = self.state['U'][:, 0].copy()
        self.state['U'][:, 0] = self.state['B'][:, 2][::-1]
        self.state['B'][:, 2] = self.state['D'][:, 0][::-1]
        self.state['D'][:, 0] = self.state['F'][:, 0]
        self.state['F'][:, 0] = temp

    def move_L_prime(self):
        self.rotate_face_ccw('L')
        temp = self.state['U'][:, 0].copy()
        self.state['U'][:, 0] = self.state['F'][:, 0]
        self.state['F'][:, 0] = self.state['D'][:, 0]
        self.state['D'][:, 0] = self.state['B'][:, 2][::-1]
        self.state['B'][:, 2] = temp[::-1]

    def move_R(self):
        self.rotate_face_cw('R')
        # Cycle: U(col2) -> B(col0) -> D(col2) -> F(col2)
        # R Clockwise: F(col2) goes up to U(col2)
        temp = self.state['U'][:, 2].copy()
        self.state['U'][:, 2] = self.state['F'][:, 2]
        self.state['F'][:, 2] = self.state['D'][:, 2]
        self.state['D'][:, 2] = self.state['B'][:, 0][::-1]
        self.state['B'][:, 0] = temp[::-1]

    def move_R_prime(self):
        self.rotate_face_ccw('R')
        temp = self.state['U'][:, 2].copy()
        self.state['U'][:, 2] = self.state['B'][:, 0][::-1]
        self.state['B'][:, 0] = self.state['D'][:, 2][::-1]
        self.state['D'][:, 2] = self.state['F'][:, 2]
        self.state['F'][:, 2] = temp

    def execute_move(self, move):
        if move == 'U': self.move_U()
        elif move == "U'": self.move_U_prime()
        elif move == 'D': self.move_D()
        elif move == "D'": self.move_D_prime()
        elif move == 'F': self.move_F()
        elif move == "F'": self.move_F_prime()
        elif move == 'B': self.move_B()
        elif move == "B'": self.move_B_prime()
        elif move == 'L': self.move_L()
        elif move == "L'": self.move_L_prime()
        elif move == 'R': self.move_R()
        elif move == "R'": self.move_R_prime()
        elif move == 'U2': self.move_U(); self.move_U()
        elif move == 'D2': self.move_D(); self.move_D()
        elif move == 'F2': self.move_F(); self.move_F()
        elif move == 'B2': self.move_B(); self.move_B()
        elif move == 'L2': self.move_L(); self.move_L()
        elif move == 'R2': self.move_R(); self.move_R()

    def get_state_string(self):
        # Converts current internal state to Kociemba string format
        # Order: U1...U9 R1...R9 F1...F9 D1...D9 L1...L9 B1...B9
        order = ['U', 'R', 'F', 'D', 'L', 'B']
        
        # Mapping internal int to Kociemba chars
        # 0->U, 1->D, 2->F, 3->B, 4->L, 5->R
        cmap = {0:'U', 1:'D', 2:'F', 3:'B', 4:'L', 5:'R'}
        
        res = ""
        for f in order:
            for r in range(3):
                for c in range(3):
                    res += cmap.get(self.state[f][r][c], 'U')
        return res

    def set_face_from_list(self, face, color_list):
        # For Edit Mode
        if len(color_list) != 9: return
        self.state[face] = np.array(color_list, dtype=int).reshape((3, 3))

    def scramble(self, n=20):
        moves = ['U', 'D', 'F', 'B', 'L', 'R']
        modifiers = ['', "'", '2']
        for _ in range(n):
            m = random.choice(moves) + random.choice(modifiers)
            self.execute_move(m)
        
    def normalize_state_for_solver(self):
        # Map center colors to Kociemba faces dynamically
        center_colors = {}
        for face in ['U', 'R', 'F', 'D', 'L', 'B']:
            center_color = self.state[face][1,1]
            center_colors[center_color] = face

        # Build string in the correct Kociemba order
        faces_order = ['U', 'R', 'F', 'D', 'L', 'B']
        result = ''
        for f in faces_order:
            for row in range(3):
                for col in range(3):
                    color = self.state[f][row, col]
                    result += center_colors[color]
        return result

