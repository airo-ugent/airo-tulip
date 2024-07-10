import copy
import math
from typing import List, Tuple

from airo_tulip.structs import PlatformLimits, Point2D, WheelConfig, WheelParamVelocity
from airo_tulip.util import get_shortest_angle


class CompliantController:
    def __init__(self, wheel_configs: List[WheelConfig]):
        self._platform_limits = PlatformLimits()

        self._target_position = [Point2D() for _ in range(len(wheel_configs))]
        self._current_position = [Point2D() for _ in range(len(wheel_configs))]
        self._target_velocity = [Point2D() for _ in range(len(wheel_configs))]
        self._current_velocity = [Point2D() for _ in range(len(wheel_configs))]
        self._last_encoders = [None] * len(wheel_configs)

        self._initialise(wheel_configs)

    def _initialise(self, wheel_configs: List[WheelConfig]) -> None:
        self._wheel_diameter = 0.105
        self._wheel_caster = 0.01
        self._wheel_distance = 0.055

        self._wheel_params = []
        for i, wheel_config in enumerate(wheel_configs):
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

            self._target_position[i] = copy.copy(wheel_param.pivot_position)
            self._current_position[i] = copy.copy(wheel_param.pivot_position)

            self._wheel_params.append(wheel_param)

    def _get_current_platform_center(self):
        s = Point2D()
        for p in self._current_position:
            s += p
        return Point2D(s.x / 4, s.y / 4)

    def calculate_wheel_target_torque(
        self, wheel_index: int, raw_encoders: List[float], delta_time: float
    ) -> Tuple[float, float]:
        """
        Returns a tuple of floats representing the target angular torque of the right and left wheel of drive `wheel_index` respectively.
        """
        self._update_current_state(wheel_index, raw_encoders, delta_time)
        msd_force_x, msd_force_y = self._calculate_mass_spring_damper_force(wheel_index)
        msd_force_r, msd_force_l = self._convert_carthesian_force_to_wheel_forces(
            wheel_index, raw_encoders[2], msd_force_x, msd_force_y
        )
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
            delta_ang_r -= 2 * math.pi
        elif delta_ang_r < -math.pi:
            delta_ang_r += 2 * math.pi

        if delta_ang_l > math.pi:
            delta_ang_l -= 2 * math.pi
        elif delta_ang_l < -math.pi:
            delta_ang_l += 2 * math.pi

        delta_pos_r = delta_ang_r * self._wheel_diameter / 2
        delta_pos_l = delta_ang_l * self._wheel_diameter / 2
        delta_pos_r *= -1  # because inverted frame
        delta_pos = (delta_pos_r + delta_pos_l) / 2

        # Calculate angle of wheels in world frame of reference
        print("CALCULATE ANGLE")
        pos_center = self._get_current_platform_center()
        print(pos_center)
        angle_platform = math.atan2(
            self._current_position[wheel_index].y - pos_center.y, self._current_position[wheel_index].x - pos_center.x
        ) - math.atan2(
            self._wheel_params[wheel_index].pivot_position.y, self._wheel_params[wheel_index].pivot_position.x
        )
        print(angle_platform)
        angle = angle_platform + self._wheel_params[wheel_index].pivot_offset + raw_encoders[2] + math.pi
        print(angle)

        # Update drive position in world
        self._current_position[wheel_index].x += delta_pos * math.cos(angle)
        self._current_position[wheel_index].y += delta_pos * math.sin(angle)
        self._current_velocity[wheel_index].x = delta_pos / delta_time * math.cos(angle)
        self._current_velocity[wheel_index].y = delta_pos / delta_time * math.sin(angle)
        self._last_encoders[wheel_index] = raw_encoders.copy()
        print(
            f"wheel {wheel_index} pos {self._current_position[wheel_index]} vel {self._current_velocity[wheel_index]}"
        )

    def _calculate_mass_spring_damper_force(self, wheel_index: int) -> Tuple[float, float]:
        spring_constant = 100.0
        damping_constant = 0.0

        position_delta = (self._current_position[wheel_index] - self._target_position[wheel_index]).norm()
        velocity_delta = (self._current_velocity[wheel_index] - self._target_velocity[wheel_index]).norm()

        force = -spring_constant * position_delta - damping_constant * velocity_delta
        if abs(force) < 1.0:
            return 0.0, 0.0

        angle = math.atan2(
            self._current_position[wheel_index].y - self._target_position[wheel_index].y,
            self._current_position[wheel_index].x - self._target_position[wheel_index].x,
        )

        force_x = force * math.cos(angle)
        force_y = force * math.sin(angle)
        return force_x, force_y

    def _convert_carthesian_force_to_wheel_forces(
        self, wheel_index: int, raw_pivot_encoder: float, force_x: float, force_y: float
    ) -> Tuple[float, float]:
        if abs(force_x) < 1.0 and abs(force_y) < 1.0:
            return 0.0, 0.0

        # Calculate angles of wheel and target force
        pos_center = self._get_current_platform_center()
        angle_platform = math.atan2(
            self._current_position[wheel_index].y - pos_center.y, self._current_position[wheel_index].x - pos_center.x
        ) - math.atan2(
            self._wheel_params[wheel_index].pivot_position.y, self._wheel_params[wheel_index].pivot_position.x
        )
        wheel_angle = angle_platform + self._wheel_params[wheel_index].pivot_offset + raw_pivot_angle
        force_angle = math.atan2(force_y, force_x)
        target_pivot_angle = force_angle - self._wheel_params[wheel_index].pivot_offset - angle_platform
        target_pivot_angle += math.pi  # wheels pull on cart, not push

        # Calculate error angle as shortest route
        angle_error = get_shortest_angle(target_pivot_angle, raw_pivot_angle)

        # Differential correction force to minimise pivot_error
        delta_force = angle_error * self._wheel_params[wheel_index].pivot_kp * 100

        # Target force of left wheel (dot product with unit pivot vector)
        force_l = force_x * math.cos(wheel_angle) + force_y * math.sin(wheel_angle)
        force_l -= delta_force

        # Target force of right wheel (dot product with unit pivot vector)
        force_r = force_x * math.cos(wheel_angle) + force_y * math.sin(wheel_angle)
        force_r += delta_force

        return -force_r, -force_l

    def _calculate_motor_controller_force(
        self, wheel_index: int, msd_force_r: float, msd_force_l: float
    ) -> Tuple[float, float]:
        return msd_force_r, msd_force_l  # no compensation for motor non-idealities

    def _convert_force_to_torque(self, force_r: float, force_l: float) -> Tuple[float, float]:
        torque_r = force_r * self._wheel_diameter / 2
        torque_l = force_l * self._wheel_diameter / 2
        return torque_r, torque_l
