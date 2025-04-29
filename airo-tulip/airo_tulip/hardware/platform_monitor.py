"""This module contains the PlatformMonitor class, which is responsible for monitoring the robot platform's state."""

import copy
import math
import time
from typing import List, Tuple

import numpy as np
import pysoem
from airo_tulip.hardware.constants import CASTOR_OFFSET, WHEEL_DISTANCE, WHEEL_RADIUS
from airo_tulip.hardware.ethercat import RxPDO1, TxPDO1
from airo_tulip.hardware.peripheral_client import PeripheralClient
from airo_tulip.hardware.structs import Attitude2DType, WheelConfig
from airo_typing import Vector3DType
from loguru import logger
from pykalman import UnscentedKalmanFilter


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


class PlatformPoseEstimatorPeripherals:
    def __init__(self):
        self._time_last_update = None
        self._pose = np.array([0.0, 0.0, 0.0])

    def _calculate_velocities(self, delta_t: float, raw_flow: List[float]):
        [flow_x_1, flow_y_1, flow_x_2, flow_y_2] = raw_flow

        T_X = 0.348  # mounting position of the flow sensor on robot
        T_Y = 0.232  # mounting position of the flow sensor on robot
        R = np.sqrt(T_X**2 + T_Y**2)
        beta = np.arctan2(T_Y, T_X)

        v_x_1 = (flow_x_1 - flow_y_1) * np.sqrt(2) / 2 / delta_t
        v_y_1 = (-flow_x_1 - flow_y_1) * np.sqrt(2) / 2 / delta_t
        v_a_1 = (-flow_x_1 * np.cos(beta) - flow_y_1 * np.sin(beta)) / R / delta_t
        v_x_2 = (-flow_x_2 + flow_y_2) * np.sqrt(2) / 2 / delta_t
        v_y_2 = (flow_x_2 + flow_y_2) * np.sqrt(2) / 2 / delta_t
        v_a_2 = (-flow_x_2 * np.cos(beta) - flow_y_2 * np.sin(beta)) / R / delta_t

        v_x = (v_x_1 + v_x_2) / 2
        v_y = (v_y_1 + v_y_2) / 2
        v_a = (v_a_1 + v_a_2) / 2

        return v_x, v_y, v_a

    def _update_pose(self, delta_t: float, v_x, v_y, p_a):
        self._pose[0] += (v_x * np.cos(p_a) - v_y * np.sin(p_a)) * delta_t
        self._pose[1] += (v_x * np.sin(p_a) + v_y * np.cos(p_a)) * delta_t
        self._pose[2] = p_a

    def get_pose(self, raw_flow: List[float], raw_orientation_x: float) -> np.ndarray:
        if self._time_last_update is None:
            self._time_last_update = time.time()
            return np.array([0.0, 0.0, 0.0])

        delta_time = time.time() - self._time_last_update
        self._time_last_update = time.time()

        v_x, v_y, v_a = self._calculate_velocities(delta_time, raw_flow)
        self._update_pose(delta_time, v_x, v_y, -raw_orientation_x)

        return self._pose


class PlatformPoseEstimatorFused:
    """Estimate the robot platform's pose and velocity based on encoder values, pivot values, and flow sensor data."""

    def __init__(self):
        """Initialise the fused pose estimator."""
        transition_covariance = np.eye(6) * 0.001**2
        observation_covariance = np.eye(5)
        observation_covariance[0:4, 0:4] *= 0.0001**2
        observation_covariance[4, 4] *= 0.001**2
        initial_state_mean = np.array([0] * 6)
        initial_state_covariance = np.eye(6) * 0.001

        self._kf = UnscentedKalmanFilter(
            self.transition_function,
            self.observation_function,
            transition_covariance,
            observation_covariance,
            initial_state_mean,
            initial_state_covariance,
        )
        self._state_mean = initial_state_mean
        self._state_covariance = initial_state_covariance

        self._time_last_update = None

    def transition_function(self, state, noise):
        """Transition function for the Kalman filter."""
        dt = self._delta_time
        F = np.eye(6)
        F[0:3, 3:6] = np.eye(3) * dt
        return np.dot(F, state) + noise

    def observation_function(self, state, noise):
        """Observation function for the Kalman filter."""
        dt = self._delta_time
        [p_x, p_y, p_a, v_x, v_y, v_a] = state[0:6]

        T_X = 0.348  # mounting position of the flow sensor on robot
        T_Y = 0.232  # mounting position of the flow sensor on robot
        R = np.sqrt(T_X**2 + T_Y**2)
        alpha = np.arctan2(T_Y, T_X)

        v_x_mobi = v_x * np.cos(p_a) + v_y * np.sin(p_a)
        v_y_mobi = -v_x * np.sin(p_a) + v_y * np.cos(p_a)

        flow_x1 = (
            np.sqrt(2) / 2 * v_x_mobi - np.sqrt(2) / 2 * v_y_mobi + R * v_a * np.cos(np.pi * 5 / 4 - alpha)
        ) * dt
        flow_y1 = (
            -np.sqrt(2) / 2 * v_x_mobi - np.sqrt(2) / 2 * v_y_mobi - R * v_a * np.sin(np.pi * 5 / 4 - alpha)
        ) * dt
        flow_x2 = (
            -np.sqrt(2) / 2 * v_x_mobi + np.sqrt(2) / 2 * v_y_mobi + R * v_a * np.cos(np.pi * 5 / 4 - alpha)
        ) * dt
        flow_y2 = (
            np.sqrt(2) / 2 * v_x_mobi + np.sqrt(2) / 2 * v_y_mobi - R * v_a * np.sin(np.pi * 5 / 4 - alpha)
        ) * dt

        orientation_x = p_a

        return np.array([flow_x1, flow_y1, flow_x2, flow_y2, orientation_x]) + noise

    def get_pose(self, raw_flow: List[float], raw_orientation_x: float) -> np.ndarray:
        """Update the robot platform's estimated pose by fusing various sensor data using a Kalman filter.

        Args:
            TODO

        Returns:
            The pose (x, y, a) of the platform."""
        if self._time_last_update is None:
            self._time_last_update = time.time()
            return np.array([0.0, 0.0, 0.0])

        self._delta_time = time.time() - self._time_last_update
        self._time_last_update = time.time()

        orientation_x = (-raw_orientation_x) % (2 * np.pi)

        observation = [*raw_flow, orientation_x]
        # print(observation)
        self._state_mean, self._state_covariance = self._kf.filter_update(
            self._state_mean, self._state_covariance, observation
        )
        # print(self._state_mean[0:3])
        return self._state_mean[0:3]


class PlatformMonitor:
    """Monitor the robot platform's state from EtherCAT messages."""

    def __init__(
        self, master: pysoem.Master, wheel_configs: List[WheelConfig], peripheral_client: PeripheralClient | None
    ):
        """Initialise the platform monitor.

        Args:
            master: The EtherCAT master.
            wheel_configs: The configurations for each drive.
            peripheral_client: The peripheral client, if available. If not available, sensor readings are affected!"""
        # Configuration.
        self._master = master
        self._wheel_configs = wheel_configs
        self._num_wheels = len(wheel_configs)
        self._peripheral_client = peripheral_client

        if self._peripheral_client is None:
            logger.warning(
                "No peripheral client detected! We will not use data from external sensors, but only from the KELO slaves."
            )

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
        self._flow: List[float]
        self._orientation: List[float]
        self._orientation_start: List[float] = None

        # Odometry.
        self._prev_encoder = [[0.0, 0.0] for _ in range(self._num_wheels)]
        self._sum_encoder = [[0.0, 0.0] for _ in range(self._num_wheels)]
        self._encoder_initialized = False
        self._odometry_pose: Attitude2DType = np.zeros((3,))
        self._odometry_velocity: Attitude2DType = np.zeros((3,))

        # Intermediate state.
        self._last_step_time: float = time.time()

        self._pose_estimator = PlatformPoseEstimator(self._num_wheels, self._wheel_configs)
        self._fused_pose_estimator = PlatformPoseEstimatorFused()
        self._peripheral_pose_estimator = PlatformPoseEstimatorPeripherals()

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

        # Read values for peripheral server
        if self._peripheral_client is not None:
            self._flow = np.array(self._peripheral_client.get_flow(), dtype=np.float64)
            self._flow /= 12750.0  # conversion from dimensionless to meters  # TODO calibrate
        else:
            self._flow = None

        if self._peripheral_client is not None:
            self._orientation = np.array(self._peripheral_client.get_orientation(), dtype=np.float64)
            self._orientation *= np.pi / 180.0  # conversion from degrees to radians
            if self._orientation_start is None:
                self._orientation_start = self._orientation.copy()
            self._orientation -= self._orientation_start
        else:
            self._orientation_start = None
            self._orientation = None

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

        # Update peripheral pose estimator
        if self._flow is not None and self._orientation is not None:
            self._peripheral_pose = self._peripheral_pose_estimator.get_pose(self._flow, self._orientation[0])
        else:
            self._peripheral_pose = self._odometry_pose

    def get_estimated_robot_pose(self) -> Attitude2DType:
        """Get the robot platform's estimated pose based on fused estimator."""
        return self._peripheral_pose

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

    def get_flow(self) -> np.ndarray | None:
        """Returns the total accumulated flow ticks for x and y"""
        return self._flow

    def get_orientation(self) -> np.ndarray | None:
        """Returns the orientation measured by the BNO055"""
        return self._orientation

    def _get_process_data(self, wheel_index: int) -> TxPDO1:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        return TxPDO1.from_buffer_copy(self._master.slaves[ethercat_index - 1].input)

    def _set_process_data(self, wheel_index: int, data: RxPDO1) -> None:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        self._master.slaves[ethercat_index - 1].output = bytes(data)

    def reset_odometry(self):
        self._odometry = np.zeros((3,))
        self._pose_estimator.reset()
