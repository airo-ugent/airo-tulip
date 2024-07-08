import math
from typing import List, Tuple

from airo_tulip.structs import PlatformLimits, WheelConfig, WheelParamVelocity


class CompliantController:
    def __init__(self, wheel_configs: List[WheelConfig]):
        self._platform_limits = PlatformLimits()

        self._target_position = [0.0] * len(wheel_configs)
        self._current_position = [0.0] * len(wheel_configs)
        self._target_velocity = [0.0] * len(wheel_configs)
        self._current_velocity = [0.0] * len(wheel_configs)
        self._last_encoders = [None] * len(wheel_configs)

        self._initialise(wheel_configs)

    def _initialise(self, wheel_configs: List[WheelConfig]) -> None:
        self._wheel_diameter = 0.105
        self._wheel_caster = 0.01
        self._wheel_distance = 0.055

        self._wheel_params = []
        for wheel_config in wheel_configs:
            wheel_param = WheelParamVelocity()

            wheel_param.relative_position_l.x = -1 * self._wheel_caster
            wheel_param.relative_position_l.y = 0.5 * self._wheel_distance
            wheel_param.relative_position_r.x = -1 * self._wheel_caster
            wheel_param.relative_position_r.y = -0.5 * self._wheel_distance

            wheel_param.angular_to_linear_velocity = 0.5 * self._wheel_diameter
            wheel_param.linear_to_angular_velocity = 1.0 / wheel_param.angular_to_linear_velocity
            wheel_param.max_linear_velocity = 100.0 * wheel_param.angular_to_linear_velocity

            wheel_param.pivot_kp = 0.2
            wheel_param._wheel_diameter = self._wheel_diameter
            wheel_param.max_pivot_error = math.pi * 0.25

            wheel_param.pivot_position.x = wheel_config.x
            wheel_param.pivot_position.y = wheel_config.y
            wheel_param.pivot_offset = wheel_config.a

            self._wheel_params.append(wheel_param)

    def calculate_wheel_target_torque(
        self, wheel_index: int, raw_encoders: List[float], delta_time: float
    ) -> Tuple[float, float]:
        """
        Returns a tuple of floats representing the target angular torque of the right and left wheel of drive `wheel_index` respectively.
        """
        self._update_current_state(wheel_index, raw_encoders, delta_time)
        msd_force_r, msd_force_l = self._calculate_mass_spring_damper_force(wheel_index)
        force_r, force_l = self._calculate_motor_controller_force(wheel_index, msd_force_r, msd_force_l)
        torque_r, torque_l = self._convert_force_to_torque(force_r, force_l)
        return torque_r, torque_l

    def _update_current_state(self, wheel_index: int, raw_encoders: List[float], delta_time: float) -> None:
        if self._last_encoders[wheel_index] is None:
            self._last_encoders[wheel_index] = raw_encoders.copy()
            return
        
        delta_ang_r = raw_encoders[0] - self._last_encoders[wheel_index][0]
        delta_ang_l = raw_encoders[1] - self._last_encoders[wheel_index][1]

        if delta_ang_r > math.pi:
            delta_ang_r -= 2*math.pi
        elif delta_ang_r < -math.pi:
            delta_ang_r += 2*math.pi

        if delta_ang_l > math.pi:
            delta_ang_l -= 2*math.pi
        elif delta_ang_l < -math.pi:
            delta_ang_l += 2*math.pi

        delta_pos_r = delta_ang_r * self._wheel_diameter / 2
        delta_pos_l = delta_ang_l * self._wheel_diameter / 2
        delta_pos_r *= -1  # because inverted frame
        delta_pos = (delta_pos_r + delta_pos_l) / 2

        self._current_position[wheel_index] += delta_pos
        self._current_velocity[wheel_index] = delta_pos / delta_time
        self._last_encoders[wheel_index] = raw_encoders.copy()
        print(
            f"wheel {wheel_index} pos {self._current_position[wheel_index]} vel {self._current_velocity[wheel_index]}"
        )

    def _calculate_mass_spring_damper_force(self, wheel_index: int) -> Tuple[float, float]:
        spring_constant = 100.0
        damping_constant = 8.0

        position_delta = self._current_position[wheel_index] - self._target_position[wheel_index]
        velocity_delta = self._current_velocity[wheel_index] - self._target_velocity[wheel_index]

        force = -spring_constant * position_delta - damping_constant * velocity_delta
        return force, force

    def _calculate_motor_controller_force(
        self, wheel_index: int, msd_force_r: float, msd_force_l: float
    ) -> Tuple[float, float]:
        return msd_force_r, msd_force_l  # no compensation for motor non-idealities

    def _convert_force_to_torque(self, force_r: float, force_l: float) -> Tuple[float, float]:
        torque_r = force_r * self._wheel_diameter / 2
        torque_l = force_l * self._wheel_diameter / 2
        return torque_r, torque_l
