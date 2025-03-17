"""Controller base class with common functionality for all controllers."""

from typing import List

import numpy as np
from airo_tulip.hardware.structs import WheelConfig, WheelParamVelocity


class Controller:
    """Controller base class with common functionality for all controllers."""

    def __init__(self, wheel_configs: List[WheelConfig]):
        """Initialise.

        Args:
            wheel_configs: The configurations for each drive."""
        self._wheel_diameter = 0.105
        self._wheel_caster = 0.01
        self._wheel_distance = 0.055

        self._wheel_params = []
        self._num_wheels = len(wheel_configs)
        for i, wheel_config in enumerate(wheel_configs):
            wheel_param = WheelParamVelocity()

            wheel_param.relative_position_l = np.array([-self._wheel_caster, 0.5 * self._wheel_distance])
            wheel_param.relative_position_r = np.array([-self._wheel_caster, -0.5 * self._wheel_distance])

            wheel_param.angular_to_linear_velocity = 0.5 * self._wheel_diameter
            wheel_param.linear_to_angular_velocity = 1.0 / wheel_param.angular_to_linear_velocity
            wheel_param.max_linear_velocity = 100.0 * wheel_param.angular_to_linear_velocity

            wheel_param.pivot_kp = 0.2
            wheel_param._wheel_diameter = self._wheel_diameter
            wheel_param.max_pivot_error = np.pi * 0.25

            wheel_param.pivot_position = np.array([wheel_config.x, wheel_config.y])
            wheel_param.pivot_offset = wheel_config.a

            self._wheel_params.append(wheel_param)
