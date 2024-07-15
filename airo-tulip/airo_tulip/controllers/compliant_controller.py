import copy
import math
from typing import List, Tuple

import rerun as rr
from airo_tulip.structs import PlatformLimits, Point2D, WheelConfig, WheelParamVelocity
from airo_tulip.util import get_shortest_angle, sign


class CompliantController:
    def __init__(self, wheel_configs: List[WheelConfig]):
        self._platform_limits = PlatformLimits()

        self._target_position = [Point2D() for _ in range(len(wheel_configs))]
        self._current_position = [Point2D() for _ in range(len(wheel_configs))]
        self._target_velocity = [Point2D() for _ in range(len(wheel_configs))]
        self._current_velocity = [Point2D() for _ in range(len(wheel_configs))]
        self._current_force = [Point2D() for _ in range(len(wheel_configs))]
        self._last_encoders = [None] * len(wheel_configs)

        self._initialise(wheel_configs)

    def _initialise(self, wheel_configs: List[WheelConfig]) -> None:
        self._wheel_diameter = 0.105
        self._wheel_caster = 0.01
        self._wheel_distance = 0.055

        self._wheel_params = []
        self._num_wheels = len(wheel_configs)
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

    def _get_current_platform_angle(self):
        v1 = self._current_position[3] - self._current_position[0]
        a1 = math.atan2(v1.y, v1.x)
        a1 += math.pi if v1.x < 0 else 0

        v2 = self._current_position[2] - self._current_position[1]
        a2 = math.atan2(v2.y, v2.x)
        a2 += math.pi if v2.x < 0 else 0

        v3 = self._current_position[1] - self._current_position[0]
        a3 = math.atan2(v3.y, v3.x) + math.pi/2
        a3 += math.pi if v3.x < 0 else 0

        v4 = self._current_position[2] - self._current_position[3]
        a4 = math.atan2(v4.y, v4.x) + math.pi/2
        a4 += math.pi if v4.x < 0 else 0

        return (a1 + a2 + a3 + a4) / 4

    def calculate_wheel_target_torque(
        self, wheel_index: int, raw_encoders: List[List[float]], delta_time: float
    ) -> Tuple[float, float]:
        """
        Returns a tuple of floats representing the target angular torque of the right and left wheel of drive `wheel_index` respectively.
        """
        if wheel_index == 0:
            for j in range(self._num_wheels):
                self._update_current_state(j, raw_encoders[j], delta_time)
                self._update_current_force(j)

        total_force = Point2D(sum([f.x for f in self._current_force]) / 4, sum([f.y for f in self._current_force]) / 4)
        if wheel_index == 0:
            rr.log(f"total_force", rr.Arrows2D(vectors=[[total_force.x, total_force.y]]))

        msd_force_r, msd_force_l = self._convert_carthesian_force_to_wheel_forces(
            wheel_index, raw_encoders[wheel_index][2], total_force.x, total_force.y
        )

        rr.log(f"force/wheel{wheel_index}/r", rr.Scalar(msd_force_r))
        rr.log(f"force/wheel{wheel_index}/l", rr.Scalar(msd_force_l))

        force_r, force_l = self._calculate_motor_controller_force(wheel_index, msd_force_r, msd_force_l)
        torque_r, torque_l = self._convert_force_to_torque(force_r, force_l)
        rr.log(f"torque/wheel{wheel_index}/r", rr.Scalar(torque_r))
        rr.log(f"torque/wheel{wheel_index}/l", rr.Scalar(torque_l))
        return torque_r, torque_l

    def _update_current_state(self, wheel_index: int, raw_encoders: List[float], delta_time: float) -> None:
        if self._last_encoders[wheel_index] is None:
            self._last_encoders[wheel_index] = raw_encoders.copy()
            return

        rr.log(f"raw_encoders/wheel{wheel_index}/1", rr.Scalar(raw_encoders[0]))
        rr.log(f"raw_encoders/wheel{wheel_index}/2", rr.Scalar(raw_encoders[1]))
        rr.log(f"raw_encoders/wheel{wheel_index}/pivot", rr.Scalar(raw_encoders[2]))

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
        delta_pos_l *= -1  # because inverted frame
        delta_pos = (delta_pos_r + delta_pos_l) / 2

        # Calculate angle of wheels in world frame of reference
        pos_center = self._get_current_platform_center()
        rr.log(f"pos_center/wheel{wheel_index}/x", rr.Scalar(pos_center.x))
        rr.log(f"pos_center/wheel{wheel_index}/y", rr.Scalar(pos_center.y))
        angle_platform = self._get_current_platform_angle()
        rr.log(f"angle_platform/wheel{wheel_index}", rr.Scalar(angle_platform))
        angle = angle_platform + self._wheel_params[wheel_index].pivot_offset + raw_encoders[2]
        rr.log(f"angle/wheel{wheel_index}", rr.Scalar(angle))

        # Update drive position in world
        self._current_position[wheel_index].x += delta_pos * math.cos(angle)
        self._current_position[wheel_index].y += delta_pos * math.sin(angle)
        self._current_velocity[wheel_index].x = delta_pos / delta_time * math.cos(angle)
        self._current_velocity[wheel_index].y = delta_pos / delta_time * math.sin(angle)
        self._last_encoders[wheel_index] = raw_encoders.copy()
        print(
            f"wheel {wheel_index} pos {self._current_position[wheel_index]} vel {self._current_velocity[wheel_index]}"
        )

        rr.log(f"pos/wheel{wheel_index}/x", rr.Scalar(self._current_position[wheel_index].x))
        rr.log(f"pos/wheel{wheel_index}/y", rr.Scalar(self._current_position[wheel_index].y))

        # Update target position to simulate movement
        #self._target_position[wheel_index].x += -0.10 * delta_time

    def _update_current_force(self, wheel_index: int) -> None:
        msd_force_x, msd_force_y = self._calculate_mass_spring_damper_force(wheel_index)
        self._current_force[wheel_index].x = msd_force_x
        self._current_force[wheel_index].y = msd_force_y

    def _calculate_mass_spring_damper_force(self, wheel_index: int) -> Tuple[float, float]:
        spring_constant = 100.0
        damping_constant = 0.0

        position_delta = (self._current_position[wheel_index] - self._target_position[wheel_index]).norm()
        velocity_delta = (self._current_velocity[wheel_index] - self._target_velocity[wheel_index]).norm()

        force = -spring_constant * position_delta - damping_constant * velocity_delta
        rr.log(f"compliant/force/wheel{wheel_index}", rr.Scalar(force))
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
        angle_platform = self._get_current_platform_angle()
        force_angle = math.atan2(force_y, force_x)
        rr.log(f"force_angle/wheel{wheel_index}", rr.Scalar(force_angle))
        target_pivot_angle = force_angle - self._wheel_params[wheel_index].pivot_offset - angle_platform
        rr.log(f"target_pivot_angle/wheel{wheel_index}", rr.Scalar(target_pivot_angle))

        # Calculate error angle as shortest route
        angle_error = get_shortest_angle(target_pivot_angle, raw_pivot_encoder)
        rr.log(f"angle_error/wheel{wheel_index}", rr.Scalar(angle_error))
        print("ANGLE", angle_error, target_pivot_angle, raw_pivot_encoder)

        # Differential correction force to minimise pivot_error
        diff_force = math.sin(angle_error) ** 2 * sign(angle_error)
        diff_force *= 1 if abs(angle_error) < math.pi / 2 else -1
        diff_force *= math.sqrt(force_x**2 + force_y**2)
        diff_force *= 1
        rr.log(f"diff_force/wheel{wheel_index}", rr.Scalar(diff_force))

        # Common force to move in target direction
        common_force = math.cos(angle_error) ** 2
        common_force *= 1 if abs(angle_error) < math.pi / 2 else -1
        common_force *= -math.sqrt(force_x**2 + force_y**2)
        rr.log(f"common_force/wheel{wheel_index}", rr.Scalar(common_force))

        # Target force of left and right wheel
        force_r = common_force + diff_force
        force_l = common_force - diff_force

        return force_r, force_l

    def _calculate_motor_controller_force(
        self, wheel_index: int, msd_force_r: float, msd_force_l: float
    ) -> Tuple[float, float]:
        return msd_force_r, msd_force_l  # no compensation for motor non-idealities

    def _convert_force_to_torque(self, force_r: float, force_l: float) -> Tuple[float, float]:
        torque_r = force_r * self._wheel_diameter / 2
        torque_l = force_l * self._wheel_diameter / 2
        return torque_r, torque_l
