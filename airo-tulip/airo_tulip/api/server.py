"""The TulipServer accepts incoming connections over TCP to send commands to the mobile robot."""

import time
from threading import Event, Thread
from typing import List

from airo_tulip.hardware.platform_driver import PlatformDriverType
from airo_tulip.hardware.robile_platform import RobilePlatform
from airo_tulip.hardware.structs import WheelConfig
from loguru import logger

from airo_tulip.api.cyclone_participant import CycloneParticipant
from airo_tulip.api.messages import Velocity, Odometry, ResetOdometry, VoltageBus, SetDriverType, \
    TOPIC_SET_TARGET_VELOCITY, TOPIC_SET_DRIVER_TYPE, TOPIC_RESET_ODOMETRY, TOPIC_ODOMETRY, TOPIC_VELOCITY, \
    TOPIC_VOLTAGE, SetVelocity
from prompt_toolkit.styles import Attrs


class RobotConfiguration:
    """The mobile robot configuration requires two parameters: an EtherCAT device string and a list of wheel configurations.

    This configuration is required to properly set up the platform and should be passed to the TulipServer's constructor."""

    def __init__(self, ecat_device: str, wheel_configs: List[WheelConfig]):
        self.ecat_device = ecat_device
        self.wheel_configs = wheel_configs


class TulipServer(CycloneParticipant):
    """The TulipServer subscribes to commands that clients send to it, and publishes the robot's state; it uses CycloneDDS to communicate."""

    def __init__(
            self,
            robot_configuration: RobotConfiguration,
            dds_domain_id: int = 129,
            loop_frequency: float = 20,
    ):
        """Initialize the server.

        Args:
            robot_configuration: The robot configuration.
            dds_domain_id: The CycloneDDS domain id (default: 129).
            loop_frequency: The frequency (Hz) with which EtherCAT messages are received and sent.
        """
        super().__init__(dds_domain_id)

        logger.info("Creating CycloneDDS topics and writers/readers.")
        self._subscribe(TOPIC_SET_TARGET_VELOCITY, SetVelocity, self._handle_set_platform_velocity_target_request)
        self._subscribe(TOPIC_SET_DRIVER_TYPE, SetDriverType, self._handle_set_driver_type_request)
        self._subscribe(TOPIC_RESET_ODOMETRY, ResetOdometry, self._handle_reset_odometry_request)

        self._register_publisher(TOPIC_VELOCITY, Velocity)
        self._register_publisher(TOPIC_ODOMETRY, Odometry)
        self._register_publisher(TOPIC_VOLTAGE, VoltageBus)
        logger.info("CycloneDDS configuration complete.")

        # Stop process flag.
        self._should_stop = Event()

        # Robot platform.
        self._platform = RobilePlatform(
            robot_configuration.ecat_device, robot_configuration.wheel_configs, PlatformDriverType.VELOCITY
        )
        self._platform.init_ethercat()

        self._loop_frequency = loop_frequency

    def _pubsub_loop(self):
        """The pub/sub loop publishes to topics and subscribes to incoming commands."""
        while not self._should_stop.is_set():
            # Publish data.
            cur_time = time.time_ns()
            if not self._platform.monitor.made_first_step():
                logger.debug("EtherCAT loop is not ready yet. Retrying in 1 second...")
                time.sleep(1.0)
                continue
            self._publish(TOPIC_ODOMETRY, Odometry(cur_time, *self._platform.monitor.get_estimated_robot_pose()))
            self._publish(TOPIC_VOLTAGE, VoltageBus(cur_time, self._platform.monitor.get_voltage_bus_max()))
            self._publish(TOPIC_VELOCITY, Velocity(cur_time, *self._platform.monitor.get_estimated_velocity()))

            # Step subscribers, handling incoming messages, if any.
            self.step()

    def _ethercat_loop(self):
        """The EtherCAT loop runs at a fixed frequency and steps the platform."""
        while not self._should_stop.is_set():
            start_ns = time.time_ns()
            self._platform.step()
            end_ns = time.time_ns()

            # Sleep if required (most likely).
            desired_duration = int((1 / self._loop_frequency) * 1e9)
            actual_duration = end_ns - start_ns
            if actual_duration < desired_duration:
                sleep_s = (desired_duration - actual_duration) * 1e-9
                logger.trace(f"Sleeping EtherCAT thread for {sleep_s} seconds.")
                time.sleep(sleep_s)

    def run(self):
        """Run the server. Starts threads that listen for requests and run the EtherCAT loop."""
        logger.info("Starting EtherCAT loop.")
        logger.info("Publishing data and subscribing to commands.")

        thread_ethercat = Thread(target=self._ethercat_loop, daemon=True)
        thread_ethercat.start()

        thread_pubsub = Thread(target=self._pubsub_loop, daemon=True)
        thread_pubsub.start()

        # Run until stop flag set by joining EtherCAT thread
        thread_ethercat.join()

    def _handle_set_platform_velocity_target_request(
            self, velocity: SetVelocity
    ):
        try:
            self._platform.driver.set_platform_velocity_target(
                velocity.x,
                velocity.y,
                velocity.a,
                velocity.duration
            )
        except ValueError as e:
            logger.error(f"Error setting platform velocity target: {e}")
        except AttributeError as e:
            logger.error(f"Error setting platform velocity target: {e}")

    def _handle_reset_odometry_request(self, reset_odometry: ResetOdometry):
        self._platform.monitor.reset_odometry()

    def _handle_set_driver_type_request(self, set_driver_type: SetDriverType):
        self._platform.driver.set_driver_type(PlatformDriverType(set_driver_type.driver_type))
