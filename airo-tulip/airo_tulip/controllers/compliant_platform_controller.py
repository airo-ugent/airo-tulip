import math
from typing import List, Tuple

import numpy as np
import rerun as rr
from airo_tulip.controllers.controller import Controller
from airo_tulip.structs import PlatformLimits, WheelConfig
from airo_tulip.util import get_shortest_angle, sign, clip_angle
from airo_typing import Vector2DType


class CompliantPlatformController(Controller):
    """Control the Robile platform by sending currents to the drives to maintain a desired position."""

    def __init__(self, wheel_configs: List[WheelConfig]):
        super().__init__(wheel_configs)

        self._platform_limits = PlatformLimits()

        num_wheels = len(wheel_configs)
        self._current_position = np.zeros((num_wheels, 2))
        self._current_velocity = np.zeros((num_wheels, 2))
        self._current_force = np.zeros((num_wheels, 2))
        self._last_encoders = [None] * num_wheels

        for i in range(num_wheels):
            self._current_position[i, 0] = wheel_configs[i].x
            self._current_position[i, 1] = wheel_configs[i].y

    def _get_current_platform_center(self) -> Vector2DType:
        """Estimate the current platform center from the drive positions (odometry based).

        Returns:
            The estimated position of the platform center relative to the origin (start position).
        """
        return np.mean(self._current_position, axis=0)

    def _get_current_platform_angle(self):
        """Compute the current platform angle.

        NOTE: Assumes there are only four wheels! TODO make generic."""
        a1 = self._get_drive_angle_estimate(3, 0)
        a2 = self._get_drive_angle_estimate(2, 1)
        a3 = self._get_drive_angle_estimate(1, 0)
        a4 = self._get_drive_angle_estimate(2, 3)

        return (a1 + a2 + a3 + a4) / 4

    def _get_drive_angle_estimate(self, drive_index_a: int, drive_index_b: int):
        v1 = self._current_position[drive_index_a] - self._current_position[drive_index_b]
        a1 = math.atan2(v1[1], v1[0])
        a1 += math.pi if v1[0] < 0 else 0
        return a1

    def calculate_wheel_target_torque(
            self, drive_index: int, raw_encoders: List[List[float]], delta_time: float
    ) -> Tuple[float, float]:
        """
        Compute the target torque for a drive based on the encoder values and the expired time since the last computation.

        Args:
            drive_index: The drive index.
            raw_encoders: Encoder values.
            delta_time: Expired time since the last invocation of this method.

        Returns:
            Target torques for the right and left wheel in this drive.
        """
        if drive_index == 0:
            for j in range(self._num_wheels):
                self._update_current_state(j, raw_encoders[j], delta_time)
                self._update_current_force(j)

        total_force = np.mean(self._current_force, axis=0)
        if drive_index == 0:
            rr.log(f"total_force", rr.Arrows2D(vectors=[total_force]))

        msd_force_r, msd_force_l = self._convert_platform_force_to_drive_forces(
            drive_index, raw_encoders[drive_index][2], total_force
        )

        rr.log(f"force/wheel{drive_index}/r", rr.Scalar(msd_force_r))
        rr.log(f"force/wheel{drive_index}/l", rr.Scalar(msd_force_l))

        force_r, force_l = self._calculate_motor_controller_force(drive_index, msd_force_r, msd_force_l)
        torque_r, torque_l = self._convert_force_to_torque(force_r, force_l)

        rr.log(f"torque/wheel{drive_index}/r", rr.Scalar(torque_r))
        rr.log(f"torque/wheel{drive_index}/l", rr.Scalar(torque_l))

        return torque_r, torque_l

    def _update_current_state(self, wheel_index: int, raw_encoders: List[float], delta_time: float) -> None:
        """Read encoder values and update the current state for the given drive.

        Args:
            wheel_index: The drive index.
            raw_encoders: Encoder values.
            delta_time: Time since last invocation of this method."""
        if self._last_encoders[wheel_index] is None:
            self._last_encoders[wheel_index] = raw_encoders.copy()
            return

        rr.log(f"raw_encoders/wheel{wheel_index}/1", rr.Scalar(raw_encoders[0]))
        rr.log(f"raw_encoders/wheel{wheel_index}/2", rr.Scalar(raw_encoders[1]))
        rr.log(f"raw_encoders/wheel{wheel_index}/pivot", rr.Scalar(raw_encoders[2]))

        delta_ang_r = raw_encoders[0] - self._last_encoders[wheel_index][0]
        delta_ang_l = raw_encoders[1] - self._last_encoders[wheel_index][1]

        delta_ang_r = clip_angle(delta_ang_r)
        delta_ang_l = clip_angle(delta_ang_l)

        delta_pos_r = delta_ang_r * self._wheel_diameter / 2
        delta_pos_l = delta_ang_l * self._wheel_diameter / 2
        delta_pos_l *= -1  # because inverted frame
        delta_pos = (delta_pos_r + delta_pos_l) / 2

        # Log the estimated platform center.
        pos_center = self._get_current_platform_center()
        rr.log(f"pos_center/wheel{wheel_index}/x", rr.Scalar(pos_center[0]))
        rr.log(f"pos_center/wheel{wheel_index}/y", rr.Scalar(pos_center[1]))

        # Calculate angle of wheels in world frame of reference
        angle_platform = self._get_current_platform_angle()
        rr.log(f"angle_platform/wheel{wheel_index}", rr.Scalar(angle_platform))
        angle = angle_platform + self._wheel_params[wheel_index].pivot_offset + raw_encoders[2]
        rr.log(f"angle/wheel{wheel_index}", rr.Scalar(angle))

        # Update drive position in world
        self._current_position[wheel_index][0] += delta_pos * math.cos(angle)
        self._current_position[wheel_index][1] += delta_pos * math.sin(angle)
        self._current_velocity[wheel_index][0] = delta_pos / delta_time * math.cos(angle)
        self._current_velocity[wheel_index][1] = delta_pos / delta_time * math.sin(angle)
        self._last_encoders[wheel_index] = raw_encoders.copy()

        rr.log(f"pos/wheel{wheel_index}/x", rr.Scalar(self._current_position[wheel_index][0]))
        rr.log(f"pos/wheel{wheel_index}/y", rr.Scalar(self._current_position[wheel_index][1]))

    def _update_current_force(self, drive_index: int) -> None:
        """Update the current force that should be applied to a drive.
        
        Args:
            drive_index: The drive index."""
        self._current_force[drive_index] = self._calculate_mass_spring_damper_force(drive_index)

    def _calculate_mass_spring_damper_force(self, drive_index: int) -> Vector2DType:
        """Calculate the spring damper force for a given drive.

        Args:
            drive_index: The drive index.

        Returns:
            The force vector."""
        spring_constant = 100.0
        damping_constant = 0.0

        position_delta = np.linalg.norm(self._current_position[drive_index])
        velocity_delta = np.linalg.norm(self._current_velocity[drive_index])

        force = -spring_constant * position_delta - damping_constant * velocity_delta
        rr.log(f"compliant/force/wheel{drive_index}", rr.Scalar(force))
        if abs(force) < 1.0:
            return np.zeros((2,))

        angle = math.atan2(self._current_position[drive_index][1], self._current_position[drive_index][0])

        force_x = force * math.cos(angle)
        force_y = force * math.sin(angle)
        return np.array([force_x, force_y])

    def _convert_platform_force_to_drive_forces(
            self, wheel_index: int, raw_pivot_encoder: float, force: Vector2DType,
    ) -> Tuple[float, float]:
        """Convert the overall platform force to the forces that should be applied to both wheels in the given drive.

        Args:
            wheel_index: The drive index.
            raw_pivot_encoder: Pivot encoder value.
            force: Platform force to be applied.

        Returns:
            Magnitudes of the force to apply to the right, resp. left wheel of this drive."""
        if abs(force[0]) < 1.0 and abs(force[1]) < 1.0:
            return 0.0, 0.0

        # Calculate angles of wheel and target force
        angle_platform = self._get_current_platform_angle()
        force_angle = math.atan2(force[1], force[0])
        rr.log(f"force_angle/wheel{wheel_index}", rr.Scalar(force_angle))
        target_pivot_angle = force_angle - self._wheel_params[wheel_index].pivot_offset - angle_platform
        rr.log(f"target_pivot_angle/wheel{wheel_index}", rr.Scalar(target_pivot_angle))

        # Calculate error angle as shortest route
        angle_error = get_shortest_angle(target_pivot_angle, raw_pivot_encoder)
        rr.log(f"angle_error/wheel{wheel_index}", rr.Scalar(angle_error))

        # Differential correction force to minimise pivot_error
        diff_force = math.sin(angle_error) ** 2 * sign(angle_error)
        diff_force *= 1 if abs(angle_error) < math.pi / 2 else -1
        diff_force *= np.linalg.norm(force)
        rr.log(f"diff_force/wheel{wheel_index}", rr.Scalar(diff_force))

        # Common force to move in target direction
        common_force = math.cos(angle_error) ** 2
        common_force *= 1 if abs(angle_error) < math.pi / 2 else -1
        common_force *= -np.linalg.norm(force)
        rr.log(f"common_force/wheel{wheel_index}", rr.Scalar(common_force))

        # Target force of left and right wheel
        force_r = common_force + diff_force
        force_l = common_force - diff_force

        return force_r, force_l

    def _calculate_motor_controller_force(
            self, wheel_index: int, msd_force_r: float, msd_force_l: float
    ) -> Tuple[float, float]:
        """Compensate for the motor."""
        return msd_force_r, msd_force_l  # no compensation for motor non-idealities

    def _convert_force_to_torque(self, force_r: float, force_l: float) -> Tuple[float, float]:
        """Convert two force values to torques."""
        torque_r = force_r * self._wheel_diameter / 2
        torque_l = force_l * self._wheel_diameter / 2
        return torque_r, torque_l
