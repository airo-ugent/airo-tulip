from dataclasses import dataclass, field

import numpy as np
from airo_typing import Vector2DType


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
class WheelParamVelocity:
    """
    Class for storing the details and geometry of each drive as a part of the complete mobile platform.
    """

    # Note: numpy arrays must use default_factory; a bare `= np.zeros((2,))` default is both a
    # shared-mutable-state footgun and rejected by `dataclass` on Python 3.11+.
    pivot_position: Vector2DType = field(default_factory=lambda: np.zeros((2,)))  # pivot location relative to vehicle centre
    pivot_offset: float = 0.0  # pivot offset relative to vehicle direction of travel
    relative_position_l: Vector2DType = field(default_factory=lambda: np.zeros((2,)))  # location of left wheel relative to pivot
    relative_position_r: Vector2DType = field(default_factory=lambda: np.zeros((2,)))  # location of right wheel relative to pivot
    linear_to_angular_velocity: float = 0.0  # scaling m/s to rad/s
    angular_to_linear_velocity: float = 0.0  # scaling rad/s to m/s
    max_linear_velocity: float = 0.0  # maximum velocity of wheel
    max_pivot_error: float = 0.0  # maximum pivot error used for error correction
    pivot_kp: float = 0.0  # proportional gain for pivot position controller
