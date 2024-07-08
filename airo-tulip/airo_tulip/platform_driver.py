import math
import time
from enum import Enum
from typing import List

import pysoem
from airo_tulip.controllers.velocity_platform_controller import VelocityPlatformController
from airo_tulip.ethercat import *
from airo_tulip.structs import WheelConfig
from airo_tulip.util import *
from loguru import logger


class PlatformDriverState(Enum):
    UNDEFINED = 0x00
    INIT = 0x01
    READY = 0x02
    ACTIVE = 0x04
    ERROR = 0x10


class PlatformDriver:
    def __init__(self, master: pysoem.Master, wheel_configs: List[WheelConfig]):
        self._master = master
        self._wheel_configs = wheel_configs
        self._num_wheels = len(wheel_configs)

        self._state = PlatformDriverState.INIT
        self._prev_encoder = [[0.0, 0.0]] * self._num_wheels
        self._sum_encoder = [[0.0, 0.0]] * self._num_wheels
        self._encoder_initialized = False
        self._current_ts = 0
        self._process_data = []
        self._wheel_enabled = [True] * self._num_wheels
        self._step_count = 0
        self._timeout = 0
        self._timeout_message_printed = True

        # Constants taken directly from KELO: https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/src/PlatformDriver.cpp
        self._wheel_distance = 0.0775
        self._wheel_diameter = 0.104
        self._current_stop = 1
        self._current_drive = 20
        self._max_v_lin = 1.5
        self._max_v_a = 1.0
        self._max_v_lin_acc = 0.0025  # per millisecond, same value for deceleration
        self._max_angle_acc = 0.01  # at vlin=0, per msec, same value for deceleration
        self._max_v_a_acc = 0.01  # per millisecond, same value for deceleration
        self._wheel_set_point_min = 0.01
        self._wheel_set_point_max = 35.0

        self._vpc = VelocityPlatformController()
        self._vpc.initialise(self._wheel_configs)

    def set_platform_velocity_target(self, vel_x: float, vel_y: float, vel_a: float, timeout: float) -> None:
        if math.sqrt(vel_x**2 + vel_y**2) > 1.0:
            raise ValueError("Cannot set target linear velocity higher than 1.0 m/s")
        if abs(vel_a) > math.pi / 8:
            raise ValueError("Cannot set target angular velocity higher than pi/8 rad/s")
        if timeout < 0.0:
            raise ValueError("Cannot set negative timeout")
        self._vpc.set_platform_velocity_target(vel_x, vel_y, vel_a)
        self._timeout = time.time() + timeout
        self._timeout_message_printed = False

    def step(self) -> bool:
        self._step_count += 1

        self._process_data = [self._get_process_data(i) for i in range(self._num_wheels)]

        for i in range(len(self._process_data)):
            pd = self._process_data[i]
            logger.trace(f"pd {i} sensor_ts {pd.sensor_ts} vel_1 {pd.velocity_1} vel_2 {pd.velocity_2}")

        self._current_ts = self._process_data[0].sensor_ts

        self._update_encoders()

        if self._timeout < time.time():
            self._vpc.set_platform_velocity_target(0.0, 0.0, 0.0)
            if not self._timeout_message_printed:
                logger.info("platform stopped early due to velocity target timeout")
                self._timeout_message_printed = True

        if self._state == PlatformDriverState.INIT:
            return self._step_init()
        if self._state == PlatformDriverState.READY:
            return self._step_ready()
        if self._state == PlatformDriverState.ACTIVE:
            return self._step_active()
        if self._state == PlatformDriverState.ERROR:
            return self._step_error()

        self._do_stop()
        return True

    def _step_init(self) -> bool:
        self._do_stop()

        ready = True
        for i in range(self._num_wheels):
            if not self._has_wheel_status_enabled(i) or self._has_wheel_status_error(i):
                ready = False

        if ready:
            self._state = PlatformDriverState.READY
            logger.info("PlatformDriver from INIT to READY")

        if self._step_count > 500 and not ready:
            logger.warning("Stopping PlatformDriver because wheels don't become ready.")
            return False

        return True

    def _step_ready(self) -> bool:
        self._do_stop()

        # TODO: check status error

        self._state = PlatformDriverState.ACTIVE
        logger.info("PlatformDriver from READY to ACTIVE")

        return True

    def _step_active(self) -> bool:
        self._do_control()
        return True

    def _step_error(self) -> bool:
        self._do_stop()
        return True

    def _has_wheel_status_enabled(self, wheel: int) -> bool:
        status1 = self._process_data[wheel].status1
        return (status1 & STAT1_ENABLED1) > 0 and (status1 & STAT1_ENABLED2) > 0

    def _has_wheel_status_error(self, wheel: int) -> bool:
        STATUS1a = 3
        STATUS1b = 63
        STATUS1disabled = 60
        STATUS2 = 2051

        process_data = self._process_data[wheel]
        status1 = process_data.status1
        status2 = process_data.status2

        return (status1 != STATUS1a and status1 != STATUS1b and status1 != STATUS1disabled) or (status2 != STATUS2)

    def _do_stop(self) -> None:
        # zero setpoints for all drives
        data = RxPDO1()
        data.timestamp = self._current_ts + 100 * 1000
        data.limit1_p = self._current_stop
        data.limit1_n = -self._current_stop
        data.limit2_p = self._current_stop
        data.limit2_n = -self._current_stop
        data.setpoint1 = 0
        data.setpoint2 = 0

        for i in range(self._num_wheels):
            data.command1 = COM1_MODE_VELOCITY
            if self._wheel_enabled[i]:
                data.command1 |= COM1_ENABLE1 | COM1_ENABLE2

            self._set_process_data(i, data)

    def _do_control(self) -> None:
        # calculate setpoints for each drive
        data = RxPDO1()
        data.timestamp = self._current_ts + 100 * 1000
        data.limit1_p = self._current_drive
        data.limit1_n = -self._current_drive
        data.limit2_p = self._current_drive
        data.limit2_n = -self._current_drive
        data.setpoint1 = 0
        data.setpoint2 = 0

        # Update desired platform velocity
        self._vpc.calculate_platform_ramped_velocities()

        for i in range(self._num_wheels):
            data.command1 = COM1_MODE_VELOCITY
            if self._wheel_enabled[i]:
                data.command1 |= COM1_ENABLE1 | COM1_ENABLE2

            # Calculate wheel target velocities
            setpoint1, setpoint2 = self._vpc.calculate_wheel_target_velocity(i, self._process_data[i].encoder_pivot)
            setpoint1 *= -1  # because of inverted frame

            # Avoid sending close to zero values
            if abs(setpoint1) < self._wheel_set_point_min:
                setpoint1 = 0
            if abs(setpoint2) < self._wheel_set_point_min:
                setpoint2 = 0

            # Avoid sending very large values
            setpoint1 = clip(setpoint1, self._wheel_set_point_max, -self._wheel_set_point_max)
            setpoint2 = clip(setpoint2, self._wheel_set_point_max, -self._wheel_set_point_max)

            # Send calculated setpoints
            data.setpoint1 = setpoint1
            data.setpoint2 = setpoint2

            logger.trace(
                f"wheel {i} enabled {self._wheel_enabled[i]} sp1 {setpoint1} sp2 {setpoint2} enc {self._process_data[i].encoder_pivot}"
            )

            self._set_process_data(i, data)

    def _update_encoders(self):
        if not self._encoder_initialized:
            for i in range(self._num_wheels):
                data = self._process_data[i]
                self._prev_encoder[i][0] = data.encoder_1
                self._prev_encoder[i][1] = data.encoder_2

        # count accumulative encoder value
        for i in range(self._num_wheels):
            data = self._process_data[i]
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

    def _get_process_data(self, wheel_index: int) -> TxPDO1:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        return TxPDO1.from_buffer_copy(self._master.slaves[ethercat_index - 1].input)

    def _set_process_data(self, wheel_index: int, data: RxPDO1) -> None:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        self._master.slaves[ethercat_index - 1].output = bytes(data)
