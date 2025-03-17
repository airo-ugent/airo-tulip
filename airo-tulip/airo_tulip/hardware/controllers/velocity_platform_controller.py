"""Control the Robile platform with velocity commands."""

import math
import time
from typing import List, Tuple

import numpy as np
import rerun as rr
from airo_tulip.hardware.controllers.controller import Controller
from airo_tulip.hardware.structs import Attitude2DType, PlatformLimits, WheelConfig, WheelParamVelocity
from airo_tulip.hardware.util import clip, clip_angle, get_shortest_angle
from airo_typing import Vector2DType


class VelocityPlatformController(Controller):
    """Control the Robile platform with velocity commands."""

    def __init__(self, wheel_configs: List[WheelConfig]):
        """Initialise the controller.

        Args:
            wheel_configs: The configurations for each drive."""
        super().__init__(wheel_configs)
        self._platform_target_vel = np.zeros((3,))
        self._platform_ramped_vel = np.zeros((3,))
        self._platform_limits = PlatformLimits()
        self._time_last_ramping: float | None = None
        self._should_align_drives = True

    @staticmethod
    def get_pivot_angle(wheel_param: WheelParamVelocity, pivot_encoder_value: float) -> float:
        """Compute the pivot angle, clipped between -pi and pi, for the current pivot rotation.

        Args:
            wheel_param: Drive parameters.
            pivot_encoder_value: Drive pivot encoder value (current pivot angle).

        Returns:
            The pivot angle."""
        return clip_angle(pivot_encoder_value - wheel_param.pivot_offset)  # [-pi, pi]

    @staticmethod
    def get_pivot_position(wheel_param: WheelParamVelocity, pivot_encoder_value: float) -> Vector2DType:
        """Compute the vector that points from the centre of the drive to the current wheel pivot.

        Args:
            wheel_param: Drive parameters.
            pivot_encoder_value: Drive pivot encoder value (current pivot angle).

        Returns:
            The position of the pivot."""
        pivot_angle = VelocityPlatformController.get_pivot_angle(wheel_param, pivot_encoder_value)
        pivot_position = np.array([np.cos(pivot_angle), np.sin(pivot_angle)])
        return pivot_position

    @staticmethod
    def wheel_positions_relative_to_platform_centre(
        wheel_param: WheelParamVelocity, pivot_encoder_value: float
    ) -> Tuple[Vector2DType, Vector2DType]:
        """For a given drive's parameters and pivot angle, compute the left and right wheel positions with respect
        to the platform centre.

        Args:
            wheel_param: Drive parameters.
            pivot_encoder_value: Drive pivot encoder value (current pivot angle).

        Returns:
            The position of the left and right wheel w.r.t. the platform centre."""
        pivot_position = VelocityPlatformController.get_pivot_position(wheel_param, pivot_encoder_value)

        # Compute position of the left wheel with respect to platform centre, taking into account the pivot's angle.
        position_l = wheel_param.pivot_position + np.array(
            [
                wheel_param.relative_position_l[0] * pivot_position[0]
                - wheel_param.relative_position_l[1] * pivot_position[1],
                wheel_param.relative_position_l[0] * pivot_position[1]
                + wheel_param.relative_position_l[1] * pivot_position[0],
            ]
        )
        # Same for right wheel.
        position_r = wheel_param.pivot_position + np.array(
            [
                wheel_param.relative_position_r[0] * pivot_position[0]
                - wheel_param.relative_position_r[1] * pivot_position[1],
                wheel_param.relative_position_r[0] * pivot_position[1]
                + wheel_param.relative_position_r[1] * pivot_position[0],
            ]
        )

        return position_l, position_r

    @staticmethod
    def velocity_at_position(target_velocity: Attitude2DType, position: Vector2DType) -> Vector2DType:
        """Given a target velocity vector at the origin (0, 0), compute the target velocity vector at a different position.

        Args:
            target_velocity: Target velocity (x, y, angular) at the origin.
            position: The position to compute the target velocity for.

        Returns:
            Target velocity at the given position.
        """
        # Linear velocity + angular velocity displacement.
        vx, vy, va = target_velocity
        x, y = position
        return np.array([vx - va * y, vy + va * x])

    def set_platform_velocity_target(self, vel_x: float, vel_y: float, vel_a: float, only_align_drives: bool) -> None:
        """Set the target velocity of the platform.

        Args:
            vel_x: The linear velocity (m/s) along the x axis.
            vel_y: The linear velocity (m/s) along the y axis.
            vel_a: The angular velocity (rad/s) around the center of the platform.
            only_align_drives: If set, does not more the platform but simply aligns the drives."""
        self._platform_target_vel[0] = 0.0 if (abs(vel_x) < 0.0000001) else vel_x
        self._platform_target_vel[1] = 0.0 if (abs(vel_y) < 0.0000001) else vel_y
        self._platform_target_vel[2] = 0.0 if (abs(vel_a) < 0.0000001) else vel_a
        self._only_align_drives = only_align_drives

    def set_platform_max_velocity(self, max_vel_linear: float, max_vel_angular: float) -> None:
        """Set the maximum velocity that the platform is allowed to drive at.

        Args:
            max_vel_linear: The maximum linear velocity (m/s).
            max_vel_angular: The maximum angular velocity (m/s)."""
        self._platform_limits.max_vel_linear = max_vel_linear
        self._platform_limits.max_vel_angular = max_vel_angular

    def set_platform_max_acceleration(self, max_acc_linear: float, max_acc_angular: float) -> None:
        """Set the maximum allowed platform acceleration."""
        self._platform_limits.max_acc_linear = max_acc_linear
        self._platform_limits.max_acc_angular = max_acc_angular

    def set_platform_max_deceleration(self, max_dec_linear: float, max_dec_angular: float) -> None:
        """Set the maximum allowed platform deceleration."""
        self._platform_limits.max_dec_linear = max_dec_linear
        self._platform_limits.max_dec_angular = max_dec_angular

    def calculate_platform_ramped_velocities(self) -> None:
        """Calculate (and store) the ramped velocities for the platform based on the (stored) target velocities."""
        now = time.time()

        # Skip first time this function is called because time_delta does not make sense otherwise
        if self._time_last_ramping is None:
            self._time_last_ramping = now

        time_delta = now - self._time_last_ramping

        # Velocity ramps
        if self._platform_ramped_vel[0] >= 0:
            self._platform_ramped_vel[0] = clip(
                self._platform_target_vel[0],
                self._platform_ramped_vel[0] + time_delta * self._platform_limits.max_acc_linear,
                self._platform_ramped_vel[0] - time_delta * self._platform_limits.max_dec_linear,
            )
        else:
            self._platform_ramped_vel[0] = clip(
                self._platform_target_vel[0],
                self._platform_ramped_vel[0] + time_delta * self._platform_limits.max_dec_linear,
                self._platform_ramped_vel[0] - time_delta * self._platform_limits.max_acc_linear,
            )

        if self._platform_ramped_vel[1] >= 0:
            self._platform_ramped_vel[1] = clip(
                self._platform_target_vel[1],
                self._platform_ramped_vel[1] + time_delta * self._platform_limits.max_acc_linear,
                self._platform_ramped_vel[1] - time_delta * self._platform_limits.max_dec_linear,
            )
        else:
            self._platform_ramped_vel[1] = clip(
                self._platform_target_vel[1],
                self._platform_ramped_vel[1] + time_delta * self._platform_limits.max_dec_linear,
                self._platform_ramped_vel[1] - time_delta * self._platform_limits.max_acc_linear,
            )

        if self._platform_ramped_vel[2] >= 0:
            self._platform_ramped_vel[2] = clip(
                self._platform_target_vel[2],
                self._platform_ramped_vel[2] + time_delta * self._platform_limits.max_acc_angular,
                self._platform_ramped_vel[2] - time_delta * self._platform_limits.max_dec_angular,
            )
        else:
            self._platform_ramped_vel[2] = clip(
                self._platform_target_vel[2],
                self._platform_ramped_vel[2] + time_delta * self._platform_limits.max_dec_angular,
                self._platform_ramped_vel[2] - time_delta * self._platform_limits.max_acc_angular,
            )

        # Velocity limits
        self._platform_ramped_vel[0] = clip(
            self._platform_ramped_vel[0], self._platform_limits.max_vel_linear, -self._platform_limits.max_vel_linear
        )
        self._platform_ramped_vel[1] = clip(
            self._platform_ramped_vel[1], self._platform_limits.max_vel_linear, -self._platform_limits.max_vel_linear
        )
        self._platform_ramped_vel[2] = clip(
            self._platform_ramped_vel[2], self._platform_limits.max_vel_angular, -self._platform_limits.max_vel_angular
        )

        self._time_last_ramping = now

    def _compute_pivot_error(self, drive_index: int, raw_pivot_angle: float) -> float:
        """Compute the raw pivot error for a given drive.

        Args:
            drive_index: Index of the drive.
            raw_pivot_angle: Encoder pivot value for this drive.

        Returns:
            Error of the drive pivot (radians) w.r.t. target angle of the platform."""
        wheel_param = self._wheel_params[drive_index]

        pivot_angle = VelocityPlatformController.get_pivot_angle(wheel_param, raw_pivot_angle)

        # Velocity target vector at pivot position
        target_vel_at_pivot = VelocityPlatformController.velocity_at_position(
            self._platform_ramped_vel, wheel_param.pivot_position
        )

        # Target pivot vector to angle
        target_pivot_angle = math.atan2(target_vel_at_pivot[1], target_vel_at_pivot[0])

        # Calculate error pivot angle as shortest route
        pivot_error = get_shortest_angle(target_pivot_angle, pivot_angle)

        return pivot_error

    def are_drives_aligned(self, encoder_pivots: List[float], max_pivot_error: float = 0.25) -> bool:
        """Returns true when all drives are approximately aligned to drive in the correct direction.

        Args:
            encoder_pivots: Encoder pivot values for all drives.
            max_pivot_error: If ALL pivot errors are smaller than this angle (radians), the drives are considered aligned.

        Returns:
            True when all drives are approximately aligned to drive in the correct direction."""
        for drive_index in range(len(self._wheel_params)):
            pivot_error = np.abs(self._compute_pivot_error(drive_index, encoder_pivots[drive_index]))
            rr.log(f"drive_{drive_index}/pivot_error", rr.Scalar(pivot_error))
            if pivot_error > max_pivot_error:
                # Reset velocity ramping so that we don't get sudden accelerations once drives are aligned.
                self._time_last_ramping = None
                return False
        return True

    def calculate_wheel_target_velocity(self, drive_index: int, raw_pivot_angle: float) -> Tuple[float, float]:
        """
        Calculate the wheel velocity setpoints based on the set target velocity.

        Args:
            drive_index: Index of the drive.
            raw_pivot_angle: Encoder pivot value for this drive.

        Returns:
            The target velocities for the right and left wheel, respectively.
        """

        # Command 0 angular vel when platform has been commanded 0 vel
        # If this is not done, then the wheels pivot to face front of platform
        # even when the platform is commanded zero velocity.
        if (
            self._platform_ramped_vel[0] == 0
            and self._platform_ramped_vel[1] == 0
            and self._platform_ramped_vel[2] == 0
        ):
            return 0.0, 0.0

        wheel_param = self._wheel_params[drive_index]

        # Pivot angle to unity vector
        unit_pivot_vector = VelocityPlatformController.get_pivot_position(wheel_param, raw_pivot_angle)

        # Position of wheels relative to platform centre
        position_l, position_r = VelocityPlatformController.wheel_positions_relative_to_platform_centre(
            wheel_param, raw_pivot_angle
        )

        # Calculate error pivot angle as shortest route
        pivot_error = self._compute_pivot_error(drive_index, raw_pivot_angle)

        # Limit pivot velocity
        pivot_error = clip(pivot_error, wheel_param.max_pivot_error, -wheel_param.max_pivot_error)

        # Target velocity vector at wheel position
        target_vel_vec_l = VelocityPlatformController.velocity_at_position(self._platform_ramped_vel, position_l)
        target_vel_vec_r = VelocityPlatformController.velocity_at_position(self._platform_ramped_vel, position_r)

        # Differential correction speed to minimise pivot_error
        delta_vel = pivot_error * wheel_param.pivot_kp

        # If all drives are not yet aligned, we should not send any forward velocities.
        # This means that the left and right wheel velocities should be equal, but with opposite sign (l = -r).
        # In other words, vel_l and vel_r (computed below) should then be 0, such that the target velocities are
        # -delta_vel and +delta_vel.
        send_forward_velocities = not self._only_align_drives

        # Target velocity of left wheel (dot product with unit pivot vector)
        vel_l = np.dot(target_vel_vec_l, unit_pivot_vector) if send_forward_velocities else 0.0
        target_vel_l = clip(vel_l - delta_vel, wheel_param.max_linear_velocity, -wheel_param.max_linear_velocity)

        # Target velocity of right wheel (dot product with unit pivot vector)
        vel_r = np.dot(target_vel_vec_r, unit_pivot_vector) if send_forward_velocities else 0.0
        target_vel_r = clip(vel_r + delta_vel, wheel_param.max_linear_velocity, -wheel_param.max_linear_velocity)

        rr.log(f"drive_{drive_index}/delta_vel", rr.Scalar(delta_vel))
        rr.log(f"drive_{drive_index}/lin_vel_l", rr.Scalar(target_vel_l))
        rr.log(f"drive_{drive_index}/lin_vel_r", rr.Scalar(target_vel_r))

        # Convert from linear to angular velocity
        target_ang_vel_l = target_vel_l * wheel_param.linear_to_angular_velocity
        target_ang_vel_r = target_vel_r * wheel_param.linear_to_angular_velocity

        return target_ang_vel_r, target_ang_vel_l


# Tests
if __name__ == "__main__":
    wheel_configs = []
    num_wheels = 4

    wc0 = WheelConfig()
    wc0.ethercat_number = 2
    wc0.x = 0.175
    wc0.y = 0.1605
    wc0.a = -2.50
    wheel_configs.append(wc0)

    wc1 = WheelConfig()
    wc1.ethercat_number = 3
    wc1.x = -0.175
    wc1.y = 0.1605
    wc1.a = 0.0
    wheel_configs.append(wc1)

    wc2 = WheelConfig()
    wc2.ethercat_number = 5
    wc2.x = -0.175
    wc2.y = -0.1605
    wc2.a = 0.0
    wheel_configs.append(wc2)

    wc3 = WheelConfig()
    wc3.ethercat_number = 6
    wc3.x = 0.175
    wc3.y = -0.1605
    wc3.a = 0.0
    wheel_configs.append(wc3)

    vpc = VelocityPlatformController(wheel_configs)

    # Set some target velocity
    vpc.set_platform_velocity_target(1.0, 0.0, 0.0, True)

    # Calculate velocities for each wheel
    for j in range(5):
        vpc.calculate_platform_ramped_velocities()
        for i in range(num_wheels):
            raw_pivot_angle = 0.0
            ang_vel_l, ang_vel_r = vpc.calculate_wheel_target_velocity(i, raw_pivot_angle)
            print(f"wheel {i} l ang vel: {ang_vel_l}")
            print(f"wheel {i} r ang vel: {ang_vel_r}")

        input()

    # Set zero target velocity
    vpc.set_platform_velocity_target(0.0, 0.0, 0.0, True)

    # Calculate velocities for each wheel
    for j in range(5):
        vpc.calculate_platform_ramped_velocities()
        for i in range(num_wheels):
            raw_pivot_angle = 0.0
            ang_vel_l, ang_vel_r = vpc.calculate_wheel_target_velocity(i, raw_pivot_angle)
            print(f"wheel {i} l ang vel: {ang_vel_l}")
            print(f"wheel {i} r ang vel: {ang_vel_r}")

        input()
