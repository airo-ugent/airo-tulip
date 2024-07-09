import math
import time

import numpy as np
import pygame
from airo_tulip.server.kelo_robile import KELORobile

pygame.init()

# Logitech F310
AXIS_LEFT_HORIZONTAL = 0
AXIS_LEFT_VERTICAL = 1
AXIS_RIGHT_HORIZONTAL = 3
AXIS_RIGHT_VERTICAL = 4
BUTTON_RIGHT_BUMPER = 5

LINEAR_SPEED_SCALING = 1.0  # joystick range: [-1, 1]. This maps it to [-LINEAR_SPEED_SCALING, LINEAR_SPEED_SCALING] m/s.
ANGULAR_SPEED_SCALING = 1.0  # analogous for angular velocity in rad/s.

if not pygame.joystick.get_init():
    exit(1)

if not pygame.joystick.get_count() > 0:
    pygame.joystick.quit()
    exit(2)

joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
joystick = joysticks[0]
print("num axes:", joystick.get_numaxes())

mobi = KELORobile("localhost", 49789)

# Get bias of controller.
axis_left_horizontal = joystick.get_axis(AXIS_LEFT_HORIZONTAL)
axis_left_vertical = joystick.get_axis(AXIS_LEFT_VERTICAL)
axis_right_horizontal = joystick.get_axis(AXIS_RIGHT_HORIZONTAL)
bias = (axis_left_horizontal, axis_left_vertical, axis_right_horizontal)

print(f"Joystick bias: {bias}")

delta_time = 0
start = time.time()
while True:
    for _event in pygame.event.get():
        pass

    # Y axis movement.
    axis_left_horizontal = joystick.get_axis(AXIS_LEFT_HORIZONTAL) - bias[0]
    # X axis movement.
    axis_left_vertical = joystick.get_axis(AXIS_LEFT_VERTICAL) - bias[1]
    # Angular movement.
    axis_right_horizontal = joystick.get_axis(AXIS_RIGHT_HORIZONTAL) - bias[2]

    vel_x = LINEAR_SPEED_SCALING * -axis_left_vertical * delta_time
    vel_y = LINEAR_SPEED_SCALING * axis_left_horizontal * delta_time
    vel_a = ANGULAR_SPEED_SCALING * axis_right_horizontal * delta_time

    vel_xy = np.array([vel_x, vel_y])
    vel_xy /= np.linalg.norm(vel_xy) + 1e-6
    vel_x, vel_y = vel_xy

    # Avoid sending small values.
    if abs(vel_x) < 0.1:
        vel_x = 0.0
    if abs(vel_y) < 0.1:
        vel_y = 0.0
    if abs(vel_a) < math.pi / 16:
        vel_a = 0.0

    if joystick.get_button(BUTTON_RIGHT_BUMPER):
        mobi.set_platform_velocity_target(vel_x, vel_y, vel_a)
    else:
        mobi.set_platform_velocity_target(0.0, 0.0, 0.0)

    now = time.time()
    delta_time = now - start
    start = now

pygame.joystick.quit()
