"""The TulipServer accepts incoming connections over TCP to send commands to the mobile robot."""

import time
from threading import Event, Thread
from typing import List

import numpy as np
import zmq
import zmq.asyncio
from airo_tulip.api.messages import (
    AreDrivesAlignedMessage,
    AreDrivesAlignedResponse,
    ErrorResponse,
    GetOdometryMessage,
    OdometryResponse,
    VelocityResponse,
    GetVelocityMessage,
    ResetOdometryMessage,
    OkResponse,
    RequestMessage,
    ResponseMessage,
    SetDriverTypeMessage,
    SetPlatformVelocityTargetMessage,
    StopServerMessage,
    HandshakeMessage,
    HandshakeResponse,
    MovePlatformToPoseMessage,
    ConcurrencyExceptionResponse,
    PositionControlLoopReachedTargetMessage,
    StopPositionControlLoopMessage
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
            MovePlatformToPoseMessage.__name__: self._handle_move_platform_to_pose_request,
            StopPositionControlLoopMessage.__name__: self._handle_stop_position_control_loop_request,
            PositionControlLoopReachedTargetMessage.__name__: self._handle_position_control_loop_reached_target_request,
        }

        # Robot platform.
        self._platform = RobilePlatform(
            robot_configuration.ecat_device, robot_configuration.wheel_configs, PlatformDriverType.VELOCITY
        )
        self._platform.init_ethercat()

        self._loop_frequency = loop_frequency

        # Position control thread.
        self._position_control_thread = None  # Will be set to a Thread if position control is active.
        self._in_position_control = False  # Will be set by the thread.
        self._stop_position_control_loop = False  # Will be set by the client and read by the thread.

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

    def _handle_move_platform_to_pose_request(self, request: MovePlatformToPoseMessage) -> ResponseMessage:
        """Handle a move platform to pose request. This starts a separate thread to perform the closed loop movement.
        Any requests that could influence this closed loop, such as `set_platform_velocity_target`, will be ignored.
        This will be signaled to the client with a `ConcurrencyExceptionResponse`.

        Args:
            request: The request message.

        Returns:
            A response message."""
        if self._in_position_control:
            logger.warning(
                "Received request to move platform to pose while already in position control. Ignoring request.")
            return ConcurrencyExceptionResponse()

        logger.info("Starting position control loop thread.")
        self._position_control_thread = Thread(target=self._position_control_loop, args=(request,))
        self._in_position_control = True
        self._position_control_thread.start()
        return OkResponse()

    def _position_control_loop(self, request: MovePlatformToPoseMessage):
        action_start_time = time.time_ns()
        action_timeout_time = action_start_time + request.timeout * 1e9

        target_pose = np.array([request.x, request.y, request.a])

        stop = False
        while not stop:
            current_pose = self._platform.monitor.get_estimated_robot_pose()
            delta_pose = target_pose - current_pose

            vel_vec_angle = np.arctan2(delta_pose[1], delta_pose[0]) - current_pose[2]
            vel_vec_norm = min(np.linalg.norm(delta_pose[:2]), 0.5)
            vel_x = vel_vec_norm * np.cos(vel_vec_angle)
            vel_y = vel_vec_norm * np.sin(vel_vec_angle)

            delta_angle = np.arctan2(np.sin(delta_pose[2]), np.cos(delta_pose[2]))
            vel_a = max(min(delta_angle, np.pi / 8), -np.pi / 8)

            command_timeout = (action_timeout_time - time.time_ns()) * 1e-9
            if command_timeout >= 0.0:
                self._platform.driver.set_platform_velocity_target(vel_x, vel_y, vel_a, timeout=command_timeout)

            at_target_pose = bool(np.linalg.norm(delta_pose) < 0.01)
            external_stop_signal = self._stop_position_control_loop or self._should_stop.is_set()
            action_timed_out = time.time_ns() - action_start_time > request.timeout * 1e9
            stop = external_stop_signal or at_target_pose or action_timed_out

        logger.info(
            "Position control loop has approximately reached target position or was requested to stop. Stopping platform completely.")
        self._platform.driver.set_platform_velocity_target(0.0, 0.0, 0.0)

        self._in_position_control = False

    def _handle_stop_position_control_loop_request(self, _request: StopPositionControlLoopMessage) -> ResponseMessage:
        """Handle a stop position control loop request. Immediately stopt the position control loop.

        Args:
            request: The request message.

        Returns:
            A response message."""
        if self._in_position_control:
            logger.info("Stopping position control loop.")
            self._stop_position_control_loop = True  # Trigger stop for thread.
            self._position_control_thread.join()  # Wait for thread to figure out it has to stop, and stop.
            self._stop_position_control_loop = False  # Reset for next request.
        else:
            logger.warning("Received request to stop position control loop, but was not in control loop at this time.")
        return OkResponse()

    def _handle_position_control_loop_reached_target_request(self, _request: PositionControlLoopReachedTargetMessage) -> ResponseMessage:
        """Handle a request to check if the position control loop has reached the target.

        Args:
            request: The request message.

        Returns:
            A response message."""
        return PositionControlLoopReachedTargetMessage(self._in_position_control)

    def _handle_set_platform_velocity_target_request(
            self, request: SetPlatformVelocityTargetMessage
    ) -> ResponseMessage:
        """Handle a set platform velocity target request.

        Args:
            request: The request message.

        Returns:
            A response message."""
        if self._in_position_control:
            logger.warning("Received request to move platform while in position control. Ignoring request.")
            return ConcurrencyExceptionResponse()

        try:
            self._platform.driver.set_platform_velocity_target(
                request.vel_x,
                request.vel_y,
                request.vel_a,
                request.timeout,
                request.only_align_drives,
            )
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
        if self._in_position_control:
            logger.warning("Received request to reset platform odometry while in position control. Ignoring request.")
            return ConcurrencyExceptionResponse()

        self._platform.monitor.reset_odometry()
        return OkResponse()

    def _handle_set_driver_type_request(self, request: SetDriverTypeMessage) -> ResponseMessage:
        """Handle a request to set the driver type (velocity or compliant mode)."""
        if self._in_position_control:
            logger.warning("Received request to set platform driver type while in position control. Ignoring request.")
            return ConcurrencyExceptionResponse()

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
