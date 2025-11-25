import pygame
from pygame.locals import *
import time
from cube_model import RubiksCube
from cube_visualizer import CubeVisualizer
from solver import solve_cube

class RubiksCubeApp:
    def __init__(self):
        self.cube = RubiksCube()
        self.visualizer = CubeVisualizer()
        
        self.running = True
        self.solving = False
        self.solution = []
        self.current_move_idx = 0
        self.move_delay = 0.3
        self.last_time = time.time()
        
        # Camera State
        self.rot_x = 30
        self.rot_y = -45
        self.zoom = -10
        
        # Edit / Step Modes
        self.step_mode = False
        self.edit_mode = False
        self.edit_queue = []
        self.edit_faces = ['U', 'R', 'F', 'D', 'L', 'B']
        self.edit_face_idx = 0

    def key_to_color_id(self, key):
        mapping = {K_w: 0, K_y: 1, K_r: 2, K_o: 3, K_g: 4, K_b: 5}
        return mapping.get(key, None)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            
            elif event.type == KEYDOWN:
                # 1. Camera
                if event.key == K_LEFT: self.rot_y -= 5
                if event.key == K_RIGHT: self.rot_y += 5
                if event.key == K_UP: self.rot_x -= 5
                if event.key == K_DOWN: self.rot_x += 5
                
                # 2. Toggle Edit Mode (E)
                if event.key == K_e:
                    self.edit_mode = not self.edit_mode
                    self.edit_queue = []
                    self.edit_face_idx = 0
                    print(f"Edit Mode: {self.edit_mode}")
                    if self.edit_mode: print(f"Enter colors for {self.edit_faces[0]} (W,Y,R,O,G,B)")
                    continue

                # 3. Edit Mode Logic
                if self.edit_mode:
                    cid = self.key_to_color_id(event.key)
                    if cid is not None:
                        self.edit_queue.append(cid)
                        print(f"Color {cid} added. ({len(self.edit_queue)}/9)")
                        if len(self.edit_queue) == 9:
                            face = self.edit_faces[self.edit_face_idx]
                            self.cube.set_face_from_list(face, self.edit_queue)
                            print(f"Face {face} set.")
                            self.edit_queue = []
                            self.edit_face_idx += 1
                            if self.edit_face_idx >= 6:
                                self.edit_mode = False
                                print("All faces set. Exiting Edit Mode.")
                                
                                state_str = self.cube.normalize_state_for_solver()
                                print("Solver input state_str:")
                                print(state_str)
                    continue

                # 4. Standard Controls
                if event.key == K_s: # Scramble
                    self.cube.scramble()
                    self.solution = []
                    print("Scrambled.")
                
                if event.key == K_r: # Reset
                    self.cube.reset()
                    self.solution = []
                    self.solving = False
                    print("Reset.")

                # 5. Solver (Auto) - SPACE
                if event.key == K_SPACE:
                    sol, err = solve_cube(self.cube)
                    if sol:
                        print(f"Solution found ({len(sol)} moves): {sol}")
                        self.solution = sol
                        self.current_move_idx = 0
                        self.solving = True
                        self.step_mode = False
                    else:
                        print("Solver Error:", err)

                # 6. Solver (Step-by-Step) - N
                if event.key == K_n:
                    if not self.solution:
                        sol, err = solve_cube(self.cube)
                        if sol:
                            self.solution = sol
                            self.current_move_idx = 0
                            self.step_mode = True
                            print(f"Solution found. Press N to step.")
                        else:
                            print("Solver Error:", err)
                    
                    # Execute next step
                    if self.solution and self.current_move_idx < len(self.solution):
                        move = self.solution[self.current_move_idx]
                        self.cube.execute_move(move)
                        self.current_move_idx += 1
                        print(f"Executed: {move}")

    def update(self):
        # Automatic Animation
        if self.solving and not self.step_mode:
            if time.time() - self.last_time > self.move_delay:
                if self.current_move_idx < len(self.solution):
                    move = self.solution[self.current_move_idx]
                    self.cube.execute_move(move)
                    self.current_move_idx += 1
                    self.last_time = time.time()
                else:
                    self.solving = False
                    print("Finished.")

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_input()
            self.update()
            self.visualizer.render(self.cube, self.rot_x, self.rot_y, self.zoom)
            clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    app = RubiksCubeApp()
    app.run()
