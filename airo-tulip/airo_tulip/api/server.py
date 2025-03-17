"""The TulipServer accepts incoming connections over TCP to send commands to the mobile robot."""

import time
from threading import Event, Thread
from typing import List

import zmq
import zmq.asyncio
from airo_tulip.api.messages import (
    AreDrivesAlignedMessage,
    AreDrivesAlignedResponse,
    ErrorResponse,
    GetOdometryMessage,
    GetVelocityMessage,
    HandshakeMessage,
    HandshakeResponse,
    OdometryResponse,
    OkResponse,
    RequestMessage,
    ResetOdometryMessage,
    ResponseMessage,
    SetDriverTypeMessage,
    SetPlatformVelocityTargetMessage,
    SetStatusLedMessage,
    StopServerMessage,
    VelocityResponse,
)
from airo_tulip.hardware.platform_driver import PlatformDriverType
from airo_tulip.hardware.robile_platform import RobilePlatform
from airo_tulip.hardware.structs import WheelConfig
from loguru import logger


class RobotConfiguration:
    """The mobile robot configuration requires two parameters: an EtherCAT device string and a list of wheel configurations.

    This configuration is required to properly set up the platform and should be passed to the TulipServer's constructor."""

    def __init__(self, ecat_device: str, wheel_configs: List[WheelConfig]):
        self.ecat_device = ecat_device
        self.wheel_configs = wheel_configs


class TulipServer:
    """The TulipServer accepts incoming connections over TCP to send commands to the mobile
    robot (Robile) platform.

    The TCP connections could come from the same machine, if you are running application code directly
    on the KELO CPU Brick, or over the network, if you are running application code on some remote device
    (e.g., your laptop, workstation, or a NUC mounted on the Robile platform.
    In any case, application code that wishes to interface with the Robile platform needs
    to communicate with the TulipServer over a TCP socket, connecting with 0MQ. We use the REQ/REP
    message pattern (https://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/patterns/client_server.html)."""

    def __init__(
        self,
        robot_configuration: RobotConfiguration,
        robot_ip: str,
        robot_port: int = 49789,
        loop_frequency: float = 20,
    ):
        """Initialize the server.

        Args:
            robot_configuration: The robot configuration.
            robot_ip: The IP address of the robot. Use 0.0.0.0 for access from the local network.
            robot_port: The port on which to run this server (default: 49789).
            loop_frequency: The frequency (Hz) with which EtherCAT messages are received and sent.
        """
        # ZMQ socket.
        address = f"tcp://{robot_ip}:{robot_port}"
        logger.info(f"Binding to {address}...")
        self._zmq_ctx = zmq.Context()
        self._zmq_socket = self._zmq_ctx.socket(zmq.REP)
        self._zmq_socket.bind(address)
        logger.info(f"Bound to {address}.")

        # Stop process flag.
        self._should_stop = Event()

        # TCP request handlers for passing instructions to the robot.
        self._request_handlers = {
            SetPlatformVelocityTargetMessage.__name__: self._handle_set_platform_velocity_target_request,
            SetDriverTypeMessage.__name__: self._handle_set_driver_type_request,
            StopServerMessage.__name__: self._handle_stop_server_request,
            GetOdometryMessage.__name__: self._handle_get_odometry_request,
            AreDrivesAlignedMessage.__name__: self._handle_are_drives_aligned_request,
            ResetOdometryMessage.__name__: self._handle_reset_odometry_request,
            GetVelocityMessage.__name__: self._handle_get_velocity_request,
            HandshakeMessage.__name__: self._handle_handshake_request,
            SetStatusLedMessage.__name__: self._handle_set_status_led_request,
        }

        # Robot platform.
        self._platform = RobilePlatform(
            robot_configuration.ecat_device, robot_configuration.wheel_configs, PlatformDriverType.VELOCITY
        )
        self._platform.init_ethercat()

        self._loop_frequency = loop_frequency

    def _request_loop(self):
        """The request loop listens for incoming requests and handles them."""
        while not self._should_stop.is_set():
            request = self._zmq_socket.recv_pyobj()
            logger.info("Handling client request.")
            response = self._handle_request(request)
            # Send response.
            logger.info("Sending response to client.")
            self._zmq_socket.send_pyobj(response)

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
        logger.info("Listening for requests.")

        thread_ethercat = Thread(target=self._ethercat_loop, daemon=True)
        thread_ethercat.start()

        thread_requests = Thread(target=self._request_loop, daemon=True)
        thread_requests.start()

        # Run until stop flag set by joining EtherCAT thread
        thread_ethercat.join()

        self._zmq_socket.close()
        self._zmq_ctx.term()

    def _handle_request(self, request: RequestMessage) -> ResponseMessage:
        """Handle a request message and return a response message.

        Args:
            request: The request message.

        Returns:
            The response."""
        # Delegate based on the request class.
        request_class_name = type(request).__name__
        logger.info(f"Request type: {request_class_name}.")
        return self._request_handlers[request_class_name](request)

    def _handle_set_platform_velocity_target_request(
        self, request: SetPlatformVelocityTargetMessage
    ) -> ResponseMessage:
        """Handle a set platform velocity target request.

        Args:
            request: The request message.

        Returns:
            A response message.

        Raises:
            An ErrorResponse if the safety limits are exceeded."""
        try:
            self._platform.driver.set_platform_velocity_target(
                request.vel_x,
                request.vel_y,
                request.vel_a,
                request.timeout,
                request.only_align_drives,
            )
            logger.info("Request handled successfully.")
            return OkResponse()
        except ValueError as e:
            logger.error(f"Safety limits exceeded: {e}")
            return ErrorResponse("Safety limits exceeded", str(e))

    def _handle_are_drives_aligned_request(self, _request: AreDrivesAlignedMessage) -> ResponseMessage:
        """Handle a request to check if the drives are aligned."""
        aligned = self._platform.driver.are_drives_aligned()
        return AreDrivesAlignedResponse(aligned)

    def _handle_reset_odometry_request(self, _request: ResetOdometryMessage) -> ResponseMessage:
        """Handle a request to reset the odometry."""
        self._platform.monitor.reset_odometry()
        return OkResponse()

    def _handle_set_driver_type_request(self, request: SetDriverTypeMessage) -> ResponseMessage:
        """Handle a request to set the driver type (velocity or compliant mode)."""
        self._platform.driver.set_driver_type(request.driver_type)
        return OkResponse()

    def _handle_stop_server_request(self, _request: StopServerMessage) -> ResponseMessage:
        """Handle a request to stop the server."""
        logger.info("Received stop request.")
        self._should_stop.set()
        return OkResponse()

    def _handle_get_odometry_request(self, _request: GetOdometryMessage) -> ResponseMessage:
        """Handle a request to get the odometry."""
        odometry = self._platform.monitor.get_estimated_robot_pose()
        return OdometryResponse(odometry)

    def _handle_get_velocity_request(self, _request: GetVelocityMessage) -> ResponseMessage:
        """Handle a request to get the velocity."""
        velocity = self._platform.monitor.get_estimated_velocity()
        return VelocityResponse(velocity)

    def _handle_handshake_request(self, request: HandshakeMessage) -> ResponseMessage:
        """Handle a handshake request."""
        logger.info("Handling handshake request.")
        return HandshakeResponse(request.uuid)

    def _handle_set_status_led_request(self, request: SetStatusLedMessage) -> ResponseMessage:
        """Handle a request to set the status of a status LED."""
        self._platform.driver.set_status_led(request.led_index, request.status)
        return OkResponse()
