from typing import Dict

import zmq
from loguru import logger
from airo_tulip.server.messages import SetPlatformVelocityTarget

class TulipServer:
    """The TulipServer accepts incoming connections over TCP to send commands to the mobile
    robot (Robile) platform.

    The TCP connections could come from the same machine, if you are running application code directly
    on the KELO CPU Brick, or over the network, if you are running application code on some remote device
    (e.g., your laptop, workstation, or a NUC mounted on the Robile platform.
    In any case, application code that wishes to interface with the Robile platform needs
    to communicate with the TulipServer over a TCP socket, connecting with 0MQ. We use the REQ/REP
    message pattern (https://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/patterns/client_server.html)."""
    def __init__(self, robot_ip: str, robot_port: int):
        # ZMQ socket.
        address = f"tcp://{robot_ip}:{robot_port}"
        logger.info(f"Binding to {address}...")
        self._zmq_ctx = zmq.Context()
        self._zmq_socket = self._zmq_ctx.socket(zmq.REP)
        self._zmq_socket.bind(address)
        logger.info(f"Bound to {address}.")

        # Stop process flag.
        self._should_stop = False

        self._request_handlers = {
            SetPlatformVelocityTarget.__class__: self._handle_set_platform_velocity_target_request
        }

    def run(self):
        logger.info("Listening for requests.")
        while not self._should_stop:
            # Wait for next client request.
            logger.info("Waiting for next client request.")
            request = self._zmq_socket.recv_pyobj()
            logger.info("Handling client request.")
            response = self._handle_request(request)
            # Send response.
            logger.info("Sending response to client.")
            self._zmq_socket.send_pyobj(response)

    def _handle_request(self, request):
        # Delegate based on the request class.
        return self._request_handlers[type(request).__class__](request)

    def _handle_set_platform_velocity_target_request(self, request: SetPlatformVelocityTarget):
        raise NotImplementedError()
