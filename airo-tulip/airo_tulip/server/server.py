import asyncio
from typing import List

import zmq
import zmq.asyncio
from loguru import logger

from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.server.messages import SetPlatformVelocityTargetMessage, ErrorResponse, OkResponse
from airo_tulip.structs import WheelConfig


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

    def __init__(self, robot_ip: str, robot_port: int, robot_configuration: RobotConfiguration,
                 loop_frequency: float = 20):
        """Initialize the server.

        Args:
            robot_ip: The IP address of the robot.
            robot_port: The port on which to run this server.
            robot_configuration: The robot configuration.
            loop_frequency: The frequency (Hz) with which EtherCAT messages are received and sent."""
        # ZMQ socket.
        address = f"tcp://{robot_ip}:{robot_port}"
        logger.info(f"Binding to {address}...")
        self._zmq_ctx = zmq.asyncio.Context()
        self._zmq_socket = self._zmq_ctx.socket(zmq.REP)
        self._zmq_socket.bind(address)
        logger.info(f"Bound to {address}.")

        # Stop process flag.
        self._should_stop = False

        # TCP request handlers for passing instructions to the robot.
        self._request_handlers = {
            SetPlatformVelocityTargetMessage.__name__: self._handle_set_platform_velocity_target_request
        }

        # Robot platform.
        self._platform = RobilePlatform(robot_configuration.ecat_device, robot_configuration.wheel_configs)
        self._platform.init_ethercat()

        self._loop_frequency = loop_frequency

    async def _get_request(self):
        request = await self._zmq_socket.recv_pyobj()
        logger.info("Handling client request.")
        response = self._handle_request(request)
        # Send response.
        logger.info("Sending response to client.")
        # Here, we block. We assume that this will be handled swiftly.
        await self._zmq_socket.send_pyobj(response)

    async def _ecat_step(self):
        self._platform.loop()
        await asyncio.sleep(1 / self._loop_frequency)

    async def run(self):
        logger.info("Listening for requests.")

        # Run both tasks concurrently. As soon as the EtherCAT step is finished, restart it.
        # Whenever the get_request task finishes, which will in most cases take longer, also restart it.
        # This gives priority to self._ecat_step() over self._get_request().
        # TODO: is there a more elegant way to structure this?
        get_request_task = asyncio.create_task(self._get_request())
        ecat_task = asyncio.create_task(self._ecat_step())
        while not self._should_stop:
            await ecat_task
            ecat_task = asyncio.create_task(self._ecat_step())
            if get_request_task.done():
                get_request_task = asyncio.create_task(self._get_request())

    def _handle_request(self, request):
        # Delegate based on the request class.
        request_class_name = type(request).__name__
        logger.trace(f"Request type: {request_class_name}.")
        return self._request_handlers[request_class_name](request)

    def _handle_set_platform_velocity_target_request(self, request: SetPlatformVelocityTargetMessage):
        try:
            self._platform.get_driver().set_platform_velocity_target(request.vel_x, request.vel_y, request.vel_a)
            logger.trace("Request handled successfully.")
            return OkResponse()
        except ValueError as e:
            logger.error(f"Safety limits exceeded: {e}")
            return ErrorResponse("Safety limits exceeded", str(e))
