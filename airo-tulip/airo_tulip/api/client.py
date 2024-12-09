"""The KELORobile client is a client that interfaces with the TulipServer (see server.py)."""
import time
from threading import Thread, Event

import numpy as np
from airo_tulip.hardware.platform_driver import PlatformDriverType
from airo_tulip.hardware.structs import Attitude2DType
from airo_typing import Vector3DType

from api.cyclone_participant import CycloneParticipant
from api.messages import Velocity, Odometry, VoltageBus, SetDriverType, ResetOdometry, TOPIC_VELOCITY, \
    TOPIC_ODOMETRY, TOPIC_VOLTAGE, TOPIC_SET_TARGET_VELOCITY, TOPIC_SET_DRIVER_TYPE, \
    TOPIC_RESET_ODOMETRY


class KELORobileError(RuntimeError):
    """Error raised when an error occurs in the KELORobile client."""

    def __init__(self, message):
        super().__init__(message)


class KELORobileClient(CycloneParticipant):
    """The KELORobileClient is a wrapper around CycloneDDS communication with the TulipServer."""

    def __init__(self, dds_domain_id: int = 129):
        """Initialize the client and connect to the server.

        Args:
            dds_domain_id: The CycloneDDS domain id (default: 129)."""
        # CycloneDDS configuration.
        super().__init__(dds_domain_id)

        self._subscribe(TOPIC_VELOCITY, Velocity, self._update_velocity)
        self._subscribe(TOPIC_ODOMETRY, Odometry, self._update_odometry)
        self._subscribe(TOPIC_VOLTAGE, VoltageBus, self._update_voltage)

        self._register_publisher(TOPIC_SET_TARGET_VELOCITY, Velocity)
        self._register_publisher(TOPIC_SET_DRIVER_TYPE, SetDriverType)
        self._register_publisher(TOPIC_RESET_ODOMETRY, ResetOdometry)

        self._latest_velocity = None
        self._latest_odometry = None
        self._latest_voltage = None

        # Start a child thread that subscribes.
        self._stop_running = Event()
        self._thread_pubsub = Thread(target=self._step, daemon=True)
        self._thread_pubsub.start()
        self._thread_pubsub.join()

    def _step(self):
        """Update subscribers."""
        # This function currently does not sleep, and runs as fast as the CPU will allow. Do we want this to enable response to commands as fast as possible?
        while not self._stop_running.is_set():
            self.step()

    def close(self):
        """Close the client."""
        self._stop_running.set()

    def _update_velocity(self, message: Velocity):
        """Update the velocity."""
        self._latest_velocity = message

    def _update_odometry(self, message: Odometry):
        """Update the odometry."""
        self._latest_odometry = message

    def _update_voltage(self, message: VoltageBus):
        """Update the voltage."""
        self._latest_voltage = message

    def set_platform_velocity_target(
            self,
            vel_x: float,
            vel_y: float,
            vel_a: float,
    ):
        """Set the x, y and angular velocity of the complete mobile platform.

        Args:
            vel_x: Linear velocity of platform in x (forward) direction in m/s.
            vel_y: Linear velocity of platform in y (left) direction in m/s.
            vel_a: Linear velocity of platform in angular direction in rad/s.
        """
        msg = Velocity(time.time_ns(), vel_x, vel_y, vel_a)
        self._publish(TOPIC_SET_TARGET_VELOCITY, msg)

    def set_driver_type(self, driver_type: PlatformDriverType):
        """Set the mode of the platform driver.

        Args:
            driver_type: Type to which the driver should be set.
        """
        msg = SetDriverType(time.time_ns(), driver_type.value)
        self._publish(TOPIC_SET_DRIVER_TYPE, msg)

    def get_odometry(self) -> Attitude2DType:
        """Get the robot platform's odometry."""
        return np.array([self._latest_odometry.x, self._latest_odometry.y,
                         self._latest_odometry.a]) if self._latest_odometry is not None else np.zeros((3,))

    def reset_odometry(self):
        """Reset the platform's odometry to 0."""
        msg = ResetOdometry(time.time_ns())
        self._publish(TOPIC_RESET_ODOMETRY, msg)

    def get_velocity(self) -> Vector3DType:
        """Get the robot platform's velocity."""
        return np.array([self._latest_velocity.x, self._latest_velocity.y,
                         self._latest_velocity.a]) if self._latest_velocity is not None else np.zeros((3,))
