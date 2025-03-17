"""Platform driver for the airo-tulip platform."""

import math
import time
from enum import Enum
from typing import List

import numpy as np
import pysoem
from airo_tulip.hardware.constants import *
from airo_tulip.hardware.controllers.velocity_platform_controller import VelocityPlatformController
from airo_tulip.hardware.ethercat import *
from airo_tulip.hardware.peripheral_client import PeripheralClient, StatusLed
from airo_tulip.hardware.structs import WheelConfig
from airo_tulip.hardware.util import *
from loguru import logger


class PlatformDriverType(Enum):
    """Platform driver type (velocity or compliant modes)."""

    VELOCITY = 1
    COMPLIANT_WEAK = 2
    COMPLIANT_MODERATE = 3
    COMPLIANT_STRONG = 4


class PlatformDriverState(Enum):
    """Platform driver state."""

    UNDEFINED = 0x00
    INIT = 0x01
    READY = 0x02
    ACTIVE = 0x04
    ERROR = 0x10


class PlatformDriver:
    """Platform driver for the airo-tulip platform."""

    def __init__(
        self,
        master: pysoem.Master,
        wheel_configs: List[WheelConfig],
        controller_type: PlatformDriverType,
        peripheral_client: PeripheralClient | None,
    ):
        """Initialise the platform driver.

        Args:
            master: The EtherCAT master.
            wheel_configs: The configurations for each drive.
            controller_type: The type of controller to use (velocity or compliant mode).
            peripheral_client: The peripheral client."""
        self._master = master
        self._wheel_configs = wheel_configs
        self._num_wheels = len(wheel_configs)

        self._peripheral_client = peripheral_client
        if self._peripheral_client is not None:
            self._peripheral_client.set_leds_boot()

        self._state = PlatformDriverState.INIT
        self._current_ts = 0
        self._process_data = []
        self._wheel_enabled = [True] * self._num_wheels
        self._step_count = 0
        self._timeout = 0
        self._timeout_message_printed = True
        self._last_step_time = None

        self._driver_type = controller_type
        self._vpc = VelocityPlatformController(self._wheel_configs)

        self._wheel_controllers = [VelocityTorqueController(self._driver_type) for _ in range(self._num_wheels * 2)]

    def set_status_led(self, index: int, status: int):
        if self._peripheral_client is not None:
            self._peripheral_client.set_status_led(StatusLed(index), bool(status))

    def set_platform_velocity_target(
        self,
        vel_x: float,
        vel_y: float,
        vel_a: float,
        timeout: float = 1.0,
        only_align_drives: bool = False,
    ) -> None:
        """Set the platform's velocity target.

        This sets a target velocity for the platform, which it will attempt to achieve. This only works if the driver
        is set to velocity mode. An internal check is done on the magnitude of the velocity to ensure safety.
        ONLY OVERRIDE THESE CHECKS IF YOU KNOW WHAT YOU ARE DOING.

        Args:
            vel_x: Velocity along X axis.
            vel_y: Velocity along Y axis.
            vel_a: Angular velocity.
            timeout: The platform will stop after this many seconds.
            only_align_drives: If true, the platform will only align the wheels in the correct orientation without driving into that directino."""
        if math.sqrt(vel_x**2 + vel_y**2) > 0.5:
            raise ValueError("Cannot set target linear velocity higher than 0.5 m/s")
        if abs(vel_a) > math.pi / 4:
            raise ValueError("Cannot set target angular velocity higher than pi/4 rad/s")
        if timeout < 0.0:
            raise ValueError("Cannot set negative timeout")

        self._vpc.set_platform_velocity_target(vel_x, vel_y, vel_a, only_align_drives)

        self._timeout = time.time() + timeout
        self._timeout_message_printed = False

    def are_drives_aligned(self) -> bool:
        """Check if the drives are aligned with the last provided velocity command."""
        encoder_pivots = [self._process_data[i].encoder_pivot for i in range(self._num_wheels)]
        return self._vpc.are_drives_aligned(encoder_pivots)

    def set_driver_type(self, driver_type: PlatformDriverType):
        """Set the driver type (velocity control or compliant control)."""
        self._driver_type = driver_type
        self._wheel_controllers = [VelocityTorqueController(driver_type) for _ in range(self._num_wheels * 2)]

    def step(self) -> bool:
        """Perform a single step of the platform driver."""
        self._step_count += 1

        self._process_data = [self._get_process_data(i) for i in range(self._num_wheels)]

        for i in range(len(self._process_data)):
            pd = self._process_data[i]
            logger.trace(f"pd {i} sensor_ts {pd.sensor_ts} vel_1 {pd.velocity_1} vel_2 {pd.velocity_2}")

        self._current_ts = self._process_data[0].sensor_ts

        if self._timeout < time.time():
            self._vpc.set_platform_velocity_target(0.0, 0.0, 0.0, only_align_drives=False)
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
        """Initialise the platform driver."""
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
        """Step the platform driver from READY to ACTIVE."""
        self._do_stop()

        # TODO: check status error

        self._state = PlatformDriverState.ACTIVE
        logger.info("PlatformDriver from READY to ACTIVE")

        return True

    def _step_active(self) -> bool:
        """Step the platform driver in ACTIVE state."""
        self._do_control()
        return True

    def _step_error(self) -> bool:
        """Step the platform driver in ERROR state."""
        self._do_stop()
        if self._peripheral_client is not None:
            self._peripheral_client.set_leds_error()
        return True

    def _has_wheel_status_enabled(self, wheel: int) -> bool:
        """Check if the wheel is enabled."""
        status1 = self._process_data[wheel].status1
        return (status1 & STAT1_ENABLED1) > 0 and (status1 & STAT1_ENABLED2) > 0

    def _has_wheel_status_error(self, wheel: int) -> bool:
        """Check if the wheel has an error."""
        STATUS1a = 3
        STATUS1b = 63
        STATUS1disabled = 60
        STATUS2 = 2051

        process_data = self._process_data[wheel]
        status1 = process_data.status1
        status2 = process_data.status2

        return (status1 != STATUS1a and status1 != STATUS1b and status1 != STATUS1disabled) or (status2 != STATUS2)

    def _do_stop(self) -> None:
        """Stop the platform."""
        # zero setpoints for all drives
        data = RxPDO1()
        data.timestamp = self._current_ts + 100 * 1000
        data.limit1_p = CURRENT_STOP
        data.limit1_n = -CURRENT_STOP
        data.limit2_p = CURRENT_STOP
        data.limit2_n = -CURRENT_STOP
        data.setpoint1 = 0
        data.setpoint2 = 0

        for i in range(self._num_wheels):
            data.command1 = COM1_MODE_VELOCITY  # we always want zero velocity (and not zero torque) when stopping

            if self._wheel_enabled[i]:
                data.command1 |= COM1_ENABLE1 | COM1_ENABLE2

            self._set_process_data(i, data)

    def _do_control(self) -> None:
        """Control the platform."""
        # calculate setpoints for each drive
        data = RxPDO1()
        data.timestamp = self._current_ts + 100 * 1000
        data.limit1_p = CURRENT_DRIVE
        data.limit1_n = -CURRENT_DRIVE
        data.limit2_p = CURRENT_DRIVE
        data.limit2_n = -CURRENT_DRIVE
        data.setpoint1 = 0
        data.setpoint2 = 0

        # Update desired platform velocity if velocity control
        self._vpc.calculate_platform_ramped_velocities()

        # Update underglow
        [vel_x, vel_y, vel_a] = self._vpc._platform_ramped_vel
        underglow_angle = np.arctan2(vel_y, vel_x)
        underglow_velocity = np.sqrt(vel_x**2 + vel_y**2)
        if self._peripheral_client is not None:
            self._peripheral_client.set_leds_active(underglow_angle, underglow_velocity)

        raw_velocities = [[pd.velocity_1, pd.velocity_2] for pd in self._process_data]

        for i in range(self._num_wheels):
            if self._driver_type == PlatformDriverType.VELOCITY:
                data.command1 = COM1_MODE_VELOCITY
            else:
                data.command1 = COM1_MODE_TORQUE

            if self._wheel_enabled[i]:
                data.command1 |= COM1_ENABLE1 | COM1_ENABLE2

            # Calculate wheel setpoints
            wheel_target_velocity_1, wheel_target_velocity_2 = self._vpc.calculate_wheel_target_velocity(
                i, self._process_data[i].encoder_pivot
            )
            wheel_target_velocity_1 *= -1  # because of inverted frame

            # Calculate setpoints
            if self._driver_type == PlatformDriverType.VELOCITY:
                setpoint1 = wheel_target_velocity_1
                setpoint2 = wheel_target_velocity_2
            else:
                # logger.debug(f"wheel_index {i}")
                setpoint1 = self._control_velocity_torque(i * 2, wheel_target_velocity_1, raw_velocities[i][0])
                setpoint2 = self._control_velocity_torque(i * 2 + 1, wheel_target_velocity_2, raw_velocities[i][1])

            # Avoid sending close to zero velocities
            if self._driver_type == PlatformDriverType.VELOCITY:
                if abs(setpoint1) < WHEEL_SET_POINT_MIN:
                    setpoint1 = 0
                if abs(setpoint2) < WHEEL_SET_POINT_MIN:
                    setpoint2 = 0

            # Avoid sending very large values
            setpoint1 = clip(setpoint1, WHEEL_SET_POINT_MAX, -WHEEL_SET_POINT_MAX)
            setpoint2 = clip(setpoint2, WHEEL_SET_POINT_MAX, -WHEEL_SET_POINT_MAX)

            # Send calculated setpoints
            data.setpoint1 = setpoint1
            data.setpoint2 = setpoint2

            logger.trace(f"wheel {i} enabled {self._wheel_enabled[i]} sp1 {setpoint1} sp2 {setpoint2}")

            self._set_process_data(i, data)

    def _control_velocity_torque(self, wheel_index, target_vel, current_vel):
        """Control the torque of a wheel."""
        controller = self._wheel_controllers[wheel_index]
        error_vel = target_vel - current_vel
        torque = controller.control(error_vel)
        # logger.debug(f"target_vel {target_vel:.2f} current_vel {current_vel:.2f} torque {torque:.2f}")
        return torque

    def _get_process_data(self, wheel_index: int) -> TxPDO1:
        """Get the process data for a wheel."""
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        return TxPDO1.from_buffer_copy(self._master.slaves[ethercat_index - 1].input)

    def _set_process_data(self, wheel_index: int, data: RxPDO1) -> None:
        """Set the process data for a wheel."""
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        self._master.slaves[ethercat_index - 1].output = bytes(data)


class VelocityTorqueController:
    """PDI Controller for torque control."""

    def __init__(self, driver_type):
        """Initialise the controller. Sets values for P, D, and I."""
        if driver_type == PlatformDriverType.COMPLIANT_MODERATE:
            self.P = 0.3
            self.D = 0.002
            self.I = 1.0
            self._max_output = 5.0
            self._max_sum_error_vel = 3.0
        elif driver_type == PlatformDriverType.COMPLIANT_STRONG:
            self.P = 0.3
            self.D = 0.005
            self.I = 1.0
            self._max_output = 10.0
            self._max_sum_error_vel = 8.0
        elif driver_type == PlatformDriverType.COMPLIANT_WEAK:
            self.P = 0.3
            self.D = 0.0
            self.I = 1.0
            self._max_output = 2.5
            self._max_sum_error_vel = 2.0

        self._prev_time = None
        self._prev_error_vel = None
        self._sum_error_vel = 0.0

    def control(self, error_vel):
        """Control the torque."""
        if self._prev_time is not None:
            delta_time = time.time() - self._prev_time
            diff_error = (error_vel - self._prev_error_vel) / delta_time
        else:
            delta_time = 0.0
            diff_error = 0.0

        torque = self.P * error_vel + self.D * diff_error + self.I * self._sum_error_vel

        self._prev_time = time.time()
        self._prev_error_vel = error_vel
        self._sum_error_vel += error_vel * delta_time
        self._sum_error_vel = clip(self._sum_error_vel, self._max_sum_error_vel, -self._max_sum_error_vel)

        torque = clip(torque, self._max_output, -self._max_output)
        return torque
