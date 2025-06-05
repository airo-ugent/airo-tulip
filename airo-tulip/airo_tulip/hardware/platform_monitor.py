"""This module contains the PlatformMonitor class, which is responsible for monitoring the robot platform's state."""

import copy
import math
import time
from typing import List, Tuple

import numpy as np
import pysoem
from airo_tulip.hardware.constants import CASTOR_OFFSET, WHEEL_DISTANCE, WHEEL_RADIUS
from airo_tulip.hardware.ethercat import RxPDO1, TxPDO1
from airo_tulip.hardware.structs import Attitude2DType, WheelConfig
from airo_typing import Vector3DType


def _norm_angle(a: float) -> float:
    """Normalize an angle to be between -PI and PI radians."""
    while a < -math.pi:
        a += math.tau
    while a > math.pi:
        a -= math.tau
    return a


class PlatformPoseEstimator:
    """Estimate the robot platform's pose and velocity based on encoder values and pivot values."""

    def __init__(self, num_drives: int, wheel_configs: List[WheelConfig]):
        """Initialise the pose estimator.

        Args:
            num_drives: The number of drives.
            wheel_configs: The configurations for each drive."""
        self._num_drives = num_drives
        self._wheel_configs = wheel_configs

        self.reset()

    def reset(self):
        """Reset the pose estimator odometry values."""
        self._prev_encoder = []  # Will be initialised on first iteration in _estimate_velocity.
        self._odom_x, self._odom_y, self._odom_a = 0, 0, 0

    def _estimate_velocity(self, dt: float, encoder_values: List[List[float]], cur_pivots: List[float]) -> np.ndarray:
        """Estimate, from the encoder values, the robot platform's linear and angular velocity.

        Args:
            dt: Seconds since last iteration.
            encoder_values: Values for the encoders for every drive (x, y, a), accumulated over time.
            cur_pivots: Current pivot values.

        Returns:
            vx, vy, va."""
        # On first iteration, return zero velocity and set state.
        if len(self._prev_encoder) == 0:
            self._prev_encoder = copy.deepcopy(encoder_values)

        vx, vy, va = 0, 0, 0

        atan_angle = CASTOR_OFFSET / WHEEL_DISTANCE

        for drive_index in range(self._num_drives):
            cur_enc = encoder_values[drive_index]
            prev_enc = self._prev_encoder[drive_index]
            wl = (cur_enc[0] - prev_enc[0]) / dt
            wr = -(cur_enc[1] - prev_enc[1]) / dt  # Negation: inverted frame.
            self._prev_encoder[drive_index] = copy.deepcopy(cur_enc)
            theta = _norm_angle(cur_pivots[drive_index] - self._wheel_configs[drive_index].a)

            vx -= WHEEL_RADIUS * (wl + wr) * np.cos(theta)
            vy -= WHEEL_RADIUS * (wl + wr) * np.sin(theta)

            wa = math.atan2(self._wheel_configs[drive_index].y, self._wheel_configs[drive_index].x)
            d = math.sqrt(self._wheel_configs[drive_index].x ** 2 + self._wheel_configs[drive_index].y ** 2)

            va += WHEEL_RADIUS * (2 * (wr - wl) * atan_angle * np.cos(theta - wa) - (wr + wl) * np.sin(theta - wa)) / d

        # Average velocities across all wheels.
        result = np.array([vx, vy, va]) / (2 * self._num_drives)

        return result

    def _estimate_pose(self, dt: float, estimated_velocity: np.ndarray) -> np.ndarray:
        """Estimate the robot platform's pose, based on its estimated velocity and previous estimations.

        Args:
            dt: Seconds since last iteration.
            estimated_velocity: The most recent velocity estimation (see _estimate_velocity).

        Returns:
            The estimated pose (x, y, a) of the platform."""
        vx, vy, va = estimated_velocity

        if abs(va) <= 0.001:
            dx = vx * dt
            dy = vy * dt
        else:
            linear_velocity = math.sqrt(vx**2 + vy**2)
            direction = math.atan2(vy, vx)

            # Displacement relative to the direction of movement.
            circle_radius = abs(linear_velocity / va)
            sign = -1 if va < 0 else 1
            da = abs(va) * dt
            dx_rel = circle_radius * np.sin(da)
            dy_rel = sign * circle_radius * (1 - np.cos(da))

            # Displacement relative to previous robot frame.
            dx = dx_rel * np.cos(direction) - dy_rel * np.sin(direction)
            dy = dx_rel * np.sin(direction) + dy_rel * np.cos(direction)

        # Displacement relative to odometry frame.
        self._odom_x += dx * np.cos(self._odom_a) - dy * np.sin(self._odom_a)
        self._odom_y += dx * np.sin(self._odom_a) + dy * np.cos(self._odom_a)
        self._odom_a = _norm_angle(self._odom_a + va * dt)

        return np.array([self._odom_x, self._odom_y, self._odom_a])

    def get_odometry(
        self, dt: float, encoder_values: List[List[float]], cur_pivots: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Get the robot platform's odometry.

        Args:
            dt: Seconds since last iteration.
            encoder_values: Values for the encoders for every drive (x, y, a), accumulated over time.
            cur_pivots: The current pivot values.

        Returns:
            The pose (x, y, a) of the platform and the velocity of the platform."""
        v = self._estimate_velocity(dt, encoder_values, cur_pivots)
        return self._estimate_pose(dt, v), v


class PlatformMonitor:
    """Monitor the robot platform's state from EtherCAT messages."""

    def __init__(self, master: pysoem.Master, wheel_configs: List[WheelConfig]):
        """Initialise the platform monitor.

        Args:
            master: The EtherCAT master.
            wheel_configs: The configurations for each drive.
            peripheral_client: The peripheral client, if available. If not available, sensor readings are affected!"""
        # Configuration.
        self._master = master
        self._wheel_configs = wheel_configs
        self._num_wheels = len(wheel_configs)

        # Monitored values.
        self._status1: List[int]
        self._status2: List[int]
        self._encoder: List[List[float]]
        self._velocity: List[List[float]]
        self._current: List[List[float]]
        self._voltage: List[List[float]]
        self._temperature: List[List[float]]
        self._voltage_bus: List[float]
        self._accel: List[List[float]]
        self._gyro: List[List[float]]
        self._pressure: List[float]
        self._current_in: List[float]

        # Odometry.
        self._prev_encoder = [[0.0, 0.0] for _ in range(self._num_wheels)]
        self._sum_encoder = [[0.0, 0.0] for _ in range(self._num_wheels)]
        self._encoder_initialized = False
        self._odometry_pose: Attitude2DType = np.zeros((3,))
        self._odometry_velocity: Attitude2DType = np.zeros((3,))

        # Intermediate state.
        self._last_step_time: float = time.time()

        self._pose_estimator = PlatformPoseEstimator(self._num_wheels, self._wheel_configs)

    @property
    def num_wheels(self) -> int:
        return self._num_wheels

    def _update_encoders(self):
        """Update the encoder values for the robot platform."""
        if not self._encoder_initialized:
            for i in range(self._num_wheels):
                data = self._get_process_data(i)
                self._prev_encoder[i][0] = data.encoder_1
                self._prev_encoder[i][1] = data.encoder_2
            self._encoder_initialized = True

        # count accumulative encoder value
        for i in range(self._num_wheels):
            data = self._get_process_data(i)
            curr_encoder1 = data.encoder_1
            curr_encoder2 = data.encoder_2

            if abs(curr_encoder1 - self._prev_encoder[i][0]) > math.pi:
                if curr_encoder1 < self._prev_encoder[i][0]:
                    self._sum_encoder[i][0] += curr_encoder1 - self._prev_encoder[i][0] + 2 * math.pi
                else:
                    self._sum_encoder[i][0] += curr_encoder1 - self._prev_encoder[i][0] - 2 * math.pi
            else:
                self._sum_encoder[i][0] += curr_encoder1 - self._prev_encoder[i][0]

            if abs(curr_encoder2 - self._prev_encoder[i][1]) > math.pi:
                if curr_encoder2 < self._prev_encoder[i][1]:
                    self._sum_encoder[i][1] += curr_encoder2 - self._prev_encoder[i][1] + 2 * math.pi
                else:
                    self._sum_encoder[i][1] += curr_encoder2 - self._prev_encoder[i][1] - 2 * math.pi
            else:
                self._sum_encoder[i][1] += curr_encoder2 - self._prev_encoder[i][1]

            self._prev_encoder[i][0] = curr_encoder1
            self._prev_encoder[i][1] = curr_encoder2

    def step(self) -> None:
        """Update the robot platform's state."""
        # Read data from drives.
        process_data = [self._get_process_data(i) for i in range(self._num_wheels)]
        self._status1 = [pd.status1 for pd in process_data]
        self._status2 = [pd.status2 for pd in process_data]
        self._encoder = [[pd.encoder_1, pd.encoder_2, pd.encoder_pivot] for pd in process_data]
        self._velocity = [[pd.velocity_1, pd.velocity_2, pd.velocity_pivot] for pd in process_data]
        self._current = [[pd.current_1_d, pd.current_2_d] for pd in process_data]
        self._voltage = [[pd.voltage_1, pd.voltage_2] for pd in process_data]
        self._temperature = [[pd.temperature_1, pd.temperature_2, pd.temperature_imu] for pd in process_data]
        self._voltage_bus = [pd.voltage_bus for pd in process_data]
        self._accel = [[pd.accel_x, pd.accel_y, pd.accel_z] for pd in process_data]
        self._gyro = [[pd.gyro_x, pd.gyro_y, pd.gyro_z] for pd in process_data]
        self._pressure = [pd.pressure for pd in process_data]
        self._current_in = [pd.current_in for pd in process_data]

        self._update_encoders()

        # Update delta time.
        now = time.time()
        delta_time = now - self._last_step_time
        self._last_step_time = now

        # Estimate odometry.
        pivots = [pd.encoder_pivot for pd in process_data]
        self._odometry_pose, self._odometry_velocity = self._pose_estimator.get_odometry(
            delta_time, self._sum_encoder, pivots
        )

    def get_estimated_robot_pose(self) -> Attitude2DType:
        """Get the robot platform's estimated pose based on fused estimator."""
        return self._odometry_pose

    def get_estimated_velocity(self) -> Vector3DType:
        """Get the robot platform's estimated velocity based on odometry."""
        return self._odometry_velocity

    def get_status1(self, wheel_index: int) -> int:
        """Returns the status1 register value for a specific drive, see `ethercat.py`."""
        return self._status1[wheel_index]

    def get_status2(self, wheel_index: int) -> int:
        """Returns the status2 register value for a specific drive, see `ethercat.py`."""
        return self._status2[wheel_index]

    def get_encoder(self, wheel_index: int) -> List[float]:
        """Returns a list of the encoder value for wheel1, wheel2 and pivot for a specific drive."""
        return self._encoder[wheel_index]

    def get_velocity(self, wheel_index: int) -> List[float]:
        """Returns a list of the velocity value for wheel1, wheel2 and pivot encoders for a specific drive."""
        return self._velocity[wheel_index]

    def get_current(self, wheel_index: int) -> List[float]:
        """Returns a list of the direct current for wheel1 and wheel2 for a specific drive."""
        return self._current[wheel_index]

    def get_voltage(self, wheel_index: int) -> List[float]:
        """Returns a list of the pwm voltage for wheel1 and wheel2 for a specific drive."""
        return self._voltage[wheel_index]

    def get_temperature(self, wheel_index: int) -> List[float]:
        """Returns a list of the temperature for wheel1, wheel2 and IMU for a specific drive."""
        return self._temperature[wheel_index]

    def get_voltage_bus(self, wheel_index: int) -> float:
        """Returns the bus voltage for a specific drive."""
        return self._voltage_bus[wheel_index]

    def get_voltage_bus_max(self) -> float:
        """Returns the maximal bus voltage of all drives."""
        return max(self._voltage_bus)

    def get_acceleration(self, wheel_index: int) -> List[float]:
        """Returns a list of the x, y and z acceleration values for IMU of a specific drive."""
        return self._accel[wheel_index]

    def get_gyro(self, wheel_index: int) -> List[float]:
        """Returns a list of the x, y and z gyro values for IMU of a specific drive."""
        return self._gyro[wheel_index]

    def get_pressure(self, wheel_index: int) -> float:
        """Returns the pressure for a specific drive."""
        return self._pressure[wheel_index]

    def get_current_in(self, wheel_index: int) -> float:
        """Returns the input current for a specific drive."""
        return self._current_in[wheel_index]

    def get_current_in_total(self) -> float:
        """Returns the total input current for all drives."""
        return sum(self._current_in)

    def get_power(self, wheel_index: int) -> float:
        """Returns the power for a specific drive."""
        return self._voltage_bus[wheel_index] * self._current_in[wheel_index]

    def get_power_total(self) -> float:
        """Returns the total power for all drives."""
        return sum([self._voltage_bus[i] * self._current_in[i] for i in range(self._num_wheels)])

    def _get_process_data(self, wheel_index: int) -> TxPDO1:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        return TxPDO1.from_buffer_copy(self._master.slaves[ethercat_index - 1].input)

    def _set_process_data(self, wheel_index: int, data: RxPDO1) -> None:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        self._master.slaves[ethercat_index - 1].output = bytes(data)

    def reset_odometry(self):
        self._odometry = np.zeros((3,))
        self._pose_estimator.reset()
