import time
from threading import Event, Thread
from typing import List

import zmq
import zmq.asyncio
from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.server.messages import (
    ErrorResponse,
    HeartbeatMessage,
    OkResponse,
    SetPlatformVelocityTargetMessage,
    StopServerMessage,
)
from airo_tulip.structs import WheelConfig
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
        robot_ip: str,
        robot_port: int,
        robot_configuration: RobotConfiguration,
        loop_frequency: float = 20,
        max_time_between_heartbeats: float = 1,
    ):
        """Initialize the server.

        Args:
            robot_ip: The IP address of the robot.
            robot_port: The port on which to run this server.
            robot_configuration: The robot configuration.
            loop_frequency: The frequency (Hz) with which EtherCAT messages are received and sent.
            max_time_between_heartbeats: The maximum time in seconds between heartbeats. If no heartbeat message was received from the client for this much time, stop everything."""
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
            StopServerMessage.__name__: self._handle_stop_server_request,
            HeartbeatMessage.__name__: self._handle_heartbeat_request,
        }

        # Robot platform.
        self._platform = RobilePlatform(robot_configuration.ecat_device, robot_configuration.wheel_configs)
        self._platform.init_ethercat()

        self._loop_frequency = loop_frequency

        self._last_heartbeat = None
        self._max_time_between_heartbeats = max_time_between_heartbeats

    def _request_loop(self):
        while not self._should_stop.is_set():
            request = self._zmq_socket.recv_pyobj()
            # As soon as we've received a request, the client should start sending out heartbeats.
            # Technically, this request could also be something else, but we should start expecting heartbeat messages.
            self._last_heartbeat = time.time()
            logger.info("Handling client request.")
            response = self._handle_request(request)
            # Send response.
            logger.info("Sending response to client.")
            self._zmq_socket.send_pyobj(response)

    def _ethercat_loop(self):
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
        logger.info("Starting EtherCAT loop.")
        logger.info("Listening for requests.")

        thread_ethercat = Thread(target=self._ethercat_loop, daemon=True)
        thread_ethercat.start()

        thread_requests = Thread(target=self._request_loop, daemon=True)
        thread_requests.start()

        while not self._should_stop.is_set():
            # Stop if we haven't received a heartbeat in a while. Safety first.
            if (
                self._last_heartbeat is not None
                and time.time() - self._last_heartbeat > self._max_time_between_heartbeats
            ):
                logger.warning("No heartbeat message received in time. Stopping platform for safety reasons!")
                self._platform.driver.set_platform_velocity_target(0.0, 0.0, 0.0)

        self._zmq_socket.close()
        self._zmq_ctx.term()

    def _handle_request(self, request):
        # Delegate based on the request class.
        request_class_name = type(request).__name__
        logger.trace(f"Request type: {request_class_name}.")
        return self._request_handlers[request_class_name](request)

    def _handle_set_platform_velocity_target_request(self, request: SetPlatformVelocityTargetMessage):
        try:
            self._platform.driver.set_platform_velocity_target(
                request.vel_x, request.vel_y, request.vel_a, request.timeout
            )
            logger.info("Request handled successfully.")
            return OkResponse()
        except ValueError as e:
            logger.error(f"Safety limits exceeded: {e}")
            return ErrorResponse("Safety limits exceeded", str(e))

    def _handle_stop_server_request(self, _request: StopServerMessage):
        logger.info("Received stop request.")
        self._should_stop.set()
        return OkResponse()

    def _handle_heartbeat_request(self, request: HeartbeatMessage):
        logger.info(f"Received heartbeat from client. Seconds since epoch (client): {request.client_time}.")
        self._last_heartbeat = time.time()
        return OkResponse()
