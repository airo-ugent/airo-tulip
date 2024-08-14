from dataclasses import dataclass

import numpy as np
from airo_typing import Vector2DType

Attitude2DType = np.ndarray
"""A (3,) np array representing a pose in 2D space with Cartesian coordinates, with `a` the angle measured from the X-axis."""


@dataclass
class PlatformLimits:
    """
    Configuration of the velocity and acceleration limits of complete mobile platform.
    """

    max_vel_linear: float = 1.0
    max_vel_angular: float = 1.0
    max_acc_linear: float = 0.5
    max_acc_angular: float = 0.8
    max_dec_linear: float = 0.5
    max_dec_angular: float = 0.8


@dataclass
class WheelConfig:
    """
    Class for storing the details and geometry of each drive as a part of the complete mobile platform.
    """

    ethercat_number: int
    x: float
    y: float
    a: float


@dataclass
class WheelData:
    enable: bool
    error: bool
    error_timestamp: bool


@dataclass
class WheelParamVelocity:
    """
    Class for storing the details and geometry of each drive as a part of the complete mobile platform.
    """

    pivot_position: Vector2DType = np.zeros((2,))  # pivot location relative to vehicle centre
    pivot_offset: float = 0.0  # pivot offset relative to vehicle direction of travel
    relative_position_l: Vector2DType = np.zeros((2,))  # location of left wheel relative to pivot
    relative_position_r: Vector2DType = np.zeros((2,))  # location of right wheel relative to pivot
    linear_to_angular_velocity: float = 0.0  # scaling m/s to rad/s
    angular_to_linear_velocity: float = 0.0  # scaling rad/s to m/s
    max_linear_velocity: float = 0.0  # maximum velocity of wheel
    max_pivot_velocity: float = 0.0  # maximum pivot error of smart wheel used for error correction
    pivot_kp: float = 0.0  # proportional gain for pivot position controller
    wheel_diameter: float = 0.0  # wheel diameter
