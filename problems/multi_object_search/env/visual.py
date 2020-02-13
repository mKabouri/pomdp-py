# Visualization of a MOS instance using pygame
#
# Note to run this file, you need to run the following
# in the parent directory of multi_object_search:
#
#   python -m multi_object_search.env.visual
# 

import pygame
import cv2
import math
import numpy as np
import random
from .env import *
from ..domain.observation import *
from ..domain.action import *
from ..world_examples import *

#### Visualization through pygame ####
class MosViz:

    def __init__(self, env,
                 res=30, fps=30, controllable=False):
        self._env = env

        self._res = res
        self._img = self._make_gridworld_image(res)
        self._last_observation = {}  # map from robot id to MosOOObservation
        
        self._controllable = controllable
        self._running = False
        self._fps = fps
        self._playtime = 0.0

    def _make_gridworld_image(self, r):
        # Preparing 2d array
        w, l = self._env.width, self._env.length
        arr2d = np.full((self._env.width,
                         self._env.length), 0)  # free grids
        state = self._env.state
        for objid in state.object_states:
            pose = state.object_states[objid]["pose"]
            if state.object_states[objid].objclass == "robot":
                arr2d[pose[0], pose[1]] = 0  # free grid
            elif state.object_states[objid].objclass == "obstacle":
                arr2d[pose[0], pose[1]] = 1  # obstacle
            elif state.object_states[objid].objclass == "target":
                arr2d[pose[0], pose[1]] = 2  # target

        # Creating image
        img = np.full((w*r,l*r,3), 255, dtype=np.int32)
        for x in range(w):
            for y in range(l):
                if arr2d[x,y] == 0:    # free
                    cv2.rectangle(img, (y*r, x*r), (y*r+r, x*r+r),
                                  (255, 255, 255), -1)
                elif arr2d[x,y] == 1:  # obstacle
                    cv2.rectangle(img, (y*r, x*r), (y*r+r, x*r+r),
                                  (40, 31, 3), -1)
                elif arr2d[x,y] == 2:  # target
                    cv2.rectangle(img, (y*r, x*r), (y*r+r, x*r+r),
                                  (255, 165, 0), -1)                    
                cv2.rectangle(img, (y*r, x*r), (y*r+r, x*r+r),
                              (0, 0, 0), 1, 8)                    
        return img
    
    @property
    def img_width(self):
        return self._img.shape[0]
    
    @property
    def img_height(self):
        return self._img.shape[1]

    @property
    def last_observation(self):
        return self._last_observation
    
    def update_observation(self, observation):
        self._last_observation = observation
        
    @staticmethod
    def draw_robot(img, x, y, th, size, color=(255,12,12)):
        radius = int(round(size / 2))
        cv2.circle(img, (y+radius, x+radius), radius, color, thickness=2)

        endpoint = (y+radius + int(round(radius*math.sin(th))),
                    x+radius + int(round(radius*math.cos(th))))
        cv2.line(img, (y+radius,x+radius), endpoint, color, 2)

    @staticmethod
    def draw_observation(img, z, rx, ry, rth, r, size, color=(12,12,255)):
        assert type(z) == MosOOObservation, "%s != MosOOObservation" % (str(type(z)))
        radius = int(round(r / 2))
        for objid in z.objposes:
            if z.for_obj(objid).pose != ObjectObservation.NULL:
                lx, ly = z.for_obj(objid).pose
                cv2.circle(img, (ly*r+radius,
                                 lx*r+radius), size, (12, 12, 255), thickness=-1)

    # PyGame interface functions
    def on_init(self):
        """pygame init"""
        pygame.init()  # calls pygame.font.init()
        # init main screen and background
        self._display_surf = pygame.display.set_mode((self.img_width,
                                                      self.img_height),
                                                     pygame.HWSURFACE)
        self._background = pygame.Surface(self._display_surf.get_size()).convert()
        self._clock = pygame.time.Clock()

        # Font
        self._myfont = pygame.font.SysFont('Comic Sans MS', 30)
        self._running = True

    def on_event(self, event):
        # TODO: Keyboard control multiple robots
        robot_id = list(self._env.robot_ids)[0]  # Just pick the first one.
        
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            u = None  # control signal according to motion model
            action = None  # control input by user

            # odometry model
            if event.key == pygame.K_LEFT:
                action = MoveLeft
            elif event.key == pygame.K_RIGHT:
                action = MoveRight
            elif event.key == pygame.K_UP:
                action = MoveForward
            elif event.key == pygame.K_DOWN:
                action = MoveBackward
            # euclidean axis model
            elif event.key == pygame.K_a:
                action = MoveWest
            elif event.key == pygame.K_d:
                action = MoveEast
            elif event.key == pygame.K_s:
                action = MoveSouth
            elif event.key == pygame.K_w:
                action = MoveNorth
            elif event.key == pygame.K_SPACE:
                action = LookAction()
            elif event.key == pygame.K_RETURN:
                action = FindAction()

            if action is None:
                return

            if self._controllable:
                if isinstance(action, MotionAction):
                    reward = self._env.state_transition(action, execute=True, robot_id=robot_id)
                    z = None
                elif isinstance(action, LookAction) or isinstance(action, FindAction):
                    robot_pose = self._env.state.pose(robot_id)
                    z = self._env.sensors[robot_id].observe(robot_pose,
                                                            self._env.state)
                    self._last_observation[robot_id] = z
                    reward = self._env.state_transition(action, execute=True, robot_id=robot_id)                    
                print("     action: %s" % str(action.name))
                print("     observation: %s" % str(z))
                print("     reward: %s" % str(reward))
                print("------------")
            return action

    def on_loop(self):
        self._playtime += self._clock.tick(self._fps) / 1000.0
        
    def on_render(self):
        # self._display_surf.blit(self._background, (0, 0))
        self.render_env(self._display_surf)
        robot_id = list(self._env.robot_ids)[0]  # Just pick the first one.        
        rx, ry, rth = self._env.state.pose(robot_id)
        fps_text = "FPS: {0:.2f}".format(self._clock.get_fps())
        pygame.display.set_caption("Robot%d(%.2f,%.2f,%.2f) | %s | %s"
                                   % (robot_id, rx, ry, rth*180/math.pi,
                                      str(self._env.state.object_states[robot_id]["objects_found"]),
                                      fps_text))
        pygame.display.flip() 
 
    def on_cleanup(self):
        pygame.quit()
 
    def on_execute(self):
        if self.on_init() == False:
            self._running = False
 
        while( self._running ):
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()

    def render_env(self, display_surf):
        # draw robot, a circle and a vector
        img = np.copy(self._img)        
        for i, robot_id in enumerate(self._env.robot_ids):
            rx, ry, rth = self._env.state.pose(robot_id)
            r = self._res  # Not radius!
            last_observation = self._last_observation.get(robot_id, None)
            if last_observation is not None:
                MosViz.draw_observation(img, last_observation,
                                        rx, ry, rth, r, r//4, color=(12,12,255*(0.8*(i+1))))
            MosViz.draw_robot(img, rx*r, ry*r, rth, r, color=(255*(0.8*(i+1)), 12, 12))
        pygame.surfarray.blit_array(display_surf, img)

def unittest():
    laserstr = make_laser_sensor(90, (1, 8), 0.5, True)
    proxstr = make_proximity_sensor(3, True)
    worldstr = equip_sensors(world3, {"r": proxstr})
    env = interpret(worldstr)
    viz = MosViz(env, controllable=True)
    viz.on_execute()

if __name__ == '__main__':
    unittest()
        
        