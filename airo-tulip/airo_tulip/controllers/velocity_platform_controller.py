import math
import time
from typing import List, Tuple

from airo_tulip.structs import Attitude2D, PlatformLimits, Point2D, WheelConfig, WheelParamVelocity
from airo_tulip.util import clip, clip_angle, get_shortest_angle


class VelocityPlatformController:
    """
    Collection of methods to control and interface with the different drives of the mobile platform.

    To be completed...
    """

    def __init__(self):
        self._platform_target_vel = Attitude2D()
        self._platform_ramped_vel = Attitude2D()
        self._platform_limits = PlatformLimits()
        self._time_last_ramping: float = None

    def initialise(self, wheel_configs: List[WheelConfig]) -> None:
        wheel_diameter = 0.105
        wheel_caster = 0.01
        wheel_distance = 0.055

        self._wheel_params = []
        for wheel_config in wheel_configs:
            wheel_param = WheelParamVelocity()

            wheel_param.relative_position_l.x = -1 * wheel_caster
            wheel_param.relative_position_l.y = 0.5 * wheel_distance
            wheel_param.relative_position_r.x = -1 * wheel_caster
            wheel_param.relative_position_r.y = -0.5 * wheel_distance

            wheel_param.angular_to_linear_velocity = 0.5 * wheel_diameter
            wheel_param.linear_to_angular_velocity = 1.0 / wheel_param.angular_to_linear_velocity
            wheel_param.max_linear_velocity = 100.0 * wheel_param.angular_to_linear_velocity

            wheel_param.pivot_kp = 0.2
            wheel_param.wheel_diameter = wheel_diameter
            wheel_param.max_pivot_error = math.pi * 0.25

            wheel_param.pivot_position.x = wheel_config.x
            wheel_param.pivot_position.y = wheel_config.y
            wheel_param.pivot_offset = wheel_config.a

            self._wheel_params.append(wheel_param)

    def set_platform_velocity_target(self, vel_x: float, vel_y: float, vel_a: float) -> None:
        self._platform_target_vel.x = 0.0 if (abs(vel_x) < 0.0000001) else vel_x
        self._platform_target_vel.y = 0.0 if (abs(vel_y) < 0.0000001) else vel_y
        self._platform_target_vel.a = 0.0 if (abs(vel_a) < 0.0000001) else vel_a

    def set_platform_max_velocity(self, max_vel_linear: float, max_vel_angular: float) -> None:
        self._platform_limits.max_vel_linear = max_vel_linear
        self._platform_limits.max_vel_angular = max_vel_angular

    def set_platform_max_acceleration(self, max_acc_linear: float, max_acc_angular: float) -> None:
        self._platform_limits.max_acc_linear = max_acc_linear
        self._platform_limits.max_acc_angular = max_acc_angular

    def set_platform_max_deceleration(self, max_dec_linear: float, max_dec_angular: float) -> None:
        self._platform_limits.max_dec_linear = max_dec_linear
        self._platform_limits.max_dec_angular = max_dec_angular

    def calculate_platform_ramped_velocities(self) -> None:
        now = time.time()

        # Skip first time this function is called because time_delta does not make sense otherwise
        if self._time_last_ramping is None:
            self._time_last_ramping = now

        time_delta = now - self._time_last_ramping

        # Velocity ramps
        if self._platform_ramped_vel.x >= 0:
            self._platform_ramped_vel.x = clip(
                self._platform_target_vel.x,
                self._platform_ramped_vel.x + time_delta * self._platform_limits.max_acc_linear,
                self._platform_ramped_vel.x - time_delta * self._platform_limits.max_dec_linear,
            )
        else:
            self._platform_ramped_vel.x = clip(
                self._platform_target_vel.x,
                self._platform_ramped_vel.x + time_delta * self._platform_limits.max_dec_linear,
                self._platform_ramped_vel.x - time_delta * self._platform_limits.max_acc_linear,
            )

        if self._platform_ramped_vel.y >= 0:
            self._platform_ramped_vel.y = clip(
                self._platform_target_vel.y,
                self._platform_ramped_vel.y + time_delta * self._platform_limits.max_acc_linear,
                self._platform_ramped_vel.y - time_delta * self._platform_limits.max_dec_linear,
            )
        else:
            self._platform_ramped_vel.y = clip(
                self._platform_target_vel.y,
                self._platform_ramped_vel.y + time_delta * self._platform_limits.max_dec_linear,
                self._platform_ramped_vel.y - time_delta * self._platform_limits.max_acc_linear,
            )

        if self._platform_ramped_vel.a >= 0:
            self._platform_ramped_vel.a = clip(
                self._platform_target_vel.a,
                self._platform_ramped_vel.a + time_delta * self._platform_limits.max_acc_angular,
                self._platform_ramped_vel.a - time_delta * self._platform_limits.max_dec_angular,
            )
        else:
            self._platform_ramped_vel.a = clip(
                self._platform_target_vel.a,
                self._platform_ramped_vel.a + time_delta * self._platform_limits.max_dec_angular,
                self._platform_ramped_vel.a - time_delta * self._platform_limits.max_acc_angular,
            )

        # Velocity limits
        self._platform_ramped_vel.x = clip(
            self._platform_ramped_vel.x, self._platform_limits.max_vel_linear, -self._platform_limits.max_vel_linear
        )
        self._platform_ramped_vel.y = clip(
            self._platform_ramped_vel.y, self._platform_limits.max_vel_linear, -self._platform_limits.max_vel_linear
        )
        self._platform_ramped_vel.a = clip(
            self._platform_ramped_vel.a, self._platform_limits.max_vel_angular, -self._platform_limits.max_vel_angular
        )

        self._time_last_ramping = now

    def calculate_wheel_target_velocity(self, wheel_index: int, raw_pivot_angle: float) -> Tuple[float, float]:
        """
        Returns a tuple of floats representing the target angular velocity of the left and right wheel of drive `wheel_index` respectively.
        """

        # Command 0 angular vel when platform has been commanded 0 vel
        # If this is not done, then the wheels pivot to face front of platform
        # even when the platform is commanded zero velocity.
        if self._platform_ramped_vel.x == 0 and self._platform_ramped_vel.y == 0 and self._platform_ramped_vel.a == 0:
            return 0.0, 0.0

        wheel_param = self._wheel_params[wheel_index]

        # Pivot angle w.r.t. front of platform (between -pi and pi)
        pivot_angle = clip_angle(raw_pivot_angle - wheel_param.pivot_offset)

        # Pivot angle to unity vector
        unit_pivot_vector = Point2D()
        unit_pivot_vector.x = math.cos(pivot_angle)
        unit_pivot_vector.y = math.sin(pivot_angle)

        # Position of wheels relative to platform centre
        position_l = Point2D()
        position_l.x = (
            wheel_param.relative_position_l.x * unit_pivot_vector.x
            - wheel_param.relative_position_l.y * unit_pivot_vector.y
        ) + wheel_param.pivot_position.x
        position_l.y = (
            wheel_param.relative_position_l.x * unit_pivot_vector.y
            + wheel_param.relative_position_l.y * unit_pivot_vector.x
        ) + wheel_param.pivot_position.y

        position_r = Point2D()
        position_r.x = (
            wheel_param.relative_position_r.x * unit_pivot_vector.x
            - wheel_param.relative_position_r.y * unit_pivot_vector.y
        ) + wheel_param.pivot_position.x
        position_r.y = (
            wheel_param.relative_position_r.x * unit_pivot_vector.y
            + wheel_param.relative_position_r.y * unit_pivot_vector.x
        ) + wheel_param.pivot_position.y

        # Velocity target vector at pivot position
        target_vel_at_pivot = Point2D()
        target_vel_at_pivot.x = self._platform_ramped_vel.x - (
            self._platform_ramped_vel.a * wheel_param.pivot_position.y
        )
        target_vel_at_pivot.y = self._platform_ramped_vel.y + (
            self._platform_ramped_vel.a * wheel_param.pivot_position.x
        )

        # Target pivot vector to angle
        target_pivot_angle = math.atan2(target_vel_at_pivot.y, target_vel_at_pivot.x)

        # Calculate error pivot angle as shortest route
        pivot_error = get_shortest_angle(target_pivot_angle, pivot_angle)

        # Limit pivot velocity
        pivot_error = clip(pivot_error, wheel_param.max_pivot_error, -wheel_param.max_pivot_error)

        # Target velocity vector at wheel position
        target_vel_vec_l = Point2D()
        target_vel_vec_l.x = self._platform_ramped_vel.x - (self._platform_ramped_vel.a * position_l.y)
        target_vel_vec_l.y = self._platform_ramped_vel.y + (self._platform_ramped_vel.a * position_l.x)

        target_vel_vec_r = Point2D()
        target_vel_vec_r.x = self._platform_ramped_vel.x - (self._platform_ramped_vel.a * position_r.y)
        target_vel_vec_r.y = self._platform_ramped_vel.y + (self._platform_ramped_vel.a * position_r.x)

        # Differential correction speed to minimise pivot_error
        delta_vel = pivot_error * wheel_param.pivot_kp

        # Target velocity of left wheel (dot product with unit pivot vector)
        vel_l = target_vel_vec_l.x * unit_pivot_vector.x + target_vel_vec_l.y * unit_pivot_vector.y
        target_vel_l = clip(vel_l - delta_vel, wheel_param.max_linear_velocity, -wheel_param.max_linear_velocity)

        # Target velocity of right wheel (dot product with unit pivot vector)
        vel_r = target_vel_vec_r.x * unit_pivot_vector.x + target_vel_vec_r.y * unit_pivot_vector.y
        target_vel_r = clip(vel_r + delta_vel, wheel_param.max_linear_velocity, -wheel_param.max_linear_velocity)

        # Convert from linear to angular velocity
        target_ang_vel_l = target_vel_l * wheel_param.linear_to_angular_velocity
        target_ang_vel_r = target_vel_r * wheel_param.linear_to_angular_velocity

        return target_ang_vel_r, target_ang_vel_l


# Tests
if __name__ == "__main__":
    # Make a new Controller object
    vpc = VelocityPlatformController()

    # Initialise the platform configuration
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

    vpc.initialise(wheel_configs)

    # Set some target velocity
    vpc.set_platform_velocity_target(1.0, 0.0, 0.0)

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
    vpc.set_platform_velocity_target(0.0, 0.0, 0.0)

    # Calculate velocities for each wheel
    for j in range(5):
        vpc.calculate_platform_ramped_velocities()
        for i in range(num_wheels):
            raw_pivot_angle = 0.0
            ang_vel_l, ang_vel_r = vpc.calculate_wheel_target_velocity(i, raw_pivot_angle)
            print(f"wheel {i} l ang vel: {ang_vel_l}")
            print(f"wheel {i} r ang vel: {ang_vel_r}")

        input()
