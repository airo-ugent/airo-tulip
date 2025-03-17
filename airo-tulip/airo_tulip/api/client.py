"""The KELORobile client is a client that interfaces with the TulipServer (see server.py)."""

from uuid import uuid4

import zmq
from airo_tulip.api.messages import (
    AreDrivesAlignedMessage,
    ErrorResponse,
    GetOdometryMessage,
    GetVelocityMessage,
    HandshakeMessage,
    RequestMessage,
    ResetOdometryMessage,
    ResponseMessage,
    SetDriverTypeMessage,
    SetPlatformVelocityTargetMessage,
    SetStatusLedMessage,
    StopServerMessage,
)
from airo_tulip.hardware.peripheral_client import StatusLed
from airo_tulip.hardware.platform_driver import PlatformDriverType
from airo_tulip.hardware.structs import Attitude2DType
from airo_typing import Vector3DType
from loguru import logger


class KELORobileError(RuntimeError):
    """Error raised when an error occurs in the KELORobile client."""

    def __init__(self, message):
        super().__init__(message)


class KELORobile:
    """The KELORobile is a client that interfaces with the TulipServer (see server.py).

    Methods are translated into network calls (essentially performing RPC). All the methods
    can raise a KELORobileError in case of an error."""

    def __init__(self, robot_ip: str, robot_port: int = 49789):
        """Initialize the client and connect to the server.

        Args:
            robot_ip: The IP address of the robot. Use 0.0.0.0 for access from the local network.
            robot_port: The port on which to run this server (default: 49789)."""
        address = f"tcp://{robot_ip}:{robot_port}"

        logger.info(f"Connecting to {address}...")
        self._zmq_ctx = zmq.Context()
        self._zmq_socket = self._zmq_ctx.socket(zmq.REQ)
        # Set timeout in milliseconds.
        self._zmq_socket.setsockopt(zmq.RCVTIMEO, 500)
        self._zmq_socket.connect(address)
        logger.info(f"Connected to {address}.")

        logger.info("Performing handshake.")
        self._handshake()
        logger.info("Connection established!")

    def _handshake(self):
        """Perform a handshake with the server to ensure the connection is established. If the server returns
        a different UUID, the connection is not properly, or if nothing is returned, the server is not running."""
        handshake_message = HandshakeMessage(str(uuid4()))
        handshake_reply = self._transceive_message(handshake_message)
        assert handshake_reply.uuid == handshake_message.uuid

    def set_platform_velocity_target(
        self,
        vel_x: float,
        vel_y: float,
        vel_a: float,
        *,
        timeout: float = 1.0,
    ) -> ResponseMessage:
        """Set the x, y and angular velocity of the complete mobile platform.

        Args:
            vel_x: Linear velocity of platform in x (forward) direction in m/s.
            vel_y: Linear velocity of platform in y (left) direction in m/s.
            vel_a: Linear velocity of platform in angular direction in rad/s.
            timeout: Duration in seconds after which the movement is automatically stopped (default 1.0).

        Returns:
            A ResponseMessage object indicating the response status of the request.
        """
        msg = SetPlatformVelocityTargetMessage(vel_x, vel_y, vel_a, timeout, False)
        return self._transceive_message(msg)

    def align_drives(self, vel_x: float, vel_y: float, vel_a: float, *, timeout: float = 1.0) -> ResponseMessage:
        """Align the drives for the given velocity values, such that they are oriented correctly. Does not send forward velocities.

        Args:
            vel_x: Linear velocity of platform in x (forward) direction in m/s.
            vel_y: Linear velocity of platform in y (left) direction in m/s.
            vel_a: Linear velocity of platform in angular direction in rad/s.
            timeout: Duration in seconds after which the movement is automatically stopped (default 1.0).

        Returns:
            A ResponseMessage object indicating the response status of the request.
        """
        msg = SetPlatformVelocityTargetMessage(vel_x, vel_y, vel_a, timeout, True)
        return self._transceive_message(msg)

    def are_drives_aligned(self) -> bool:
        """Check whether the drives are aligned with the last sent velocity command orientation.

        Returns:
            A boolean indicating the alignment."""
        msg = AreDrivesAlignedMessage()
        return self._transceive_message(msg).aligned

    def set_driver_type(self, driver_type: PlatformDriverType) -> ResponseMessage:
        """Set the mode of the platform driver.

        Args:
            driver_type: Type to which the driver should be set.

        Returns:
            A ResponseMessage object indicating the response status of the request.
        """
        msg = SetDriverTypeMessage(driver_type)
        return self._transceive_message(msg)

    def stop_server(self) -> ResponseMessage:
        """Stops the remote server.

        Returns:
            A ResponseMessage object indicating the response status of the request.
        """
        msg = StopServerMessage()
        return self._transceive_message(msg)

    def get_odometry(self) -> Attitude2DType:
        """Get the robot platform's odometry."""
        msg = GetOdometryMessage()
        return self._transceive_message(msg).odometry

    def reset_odometry(self):
        """Reset the platform's odometry to 0."""
        msg = ResetOdometryMessage()
        self._transceive_message(msg)

    def get_velocity(self) -> Vector3DType:
        """Get the robot platform's velocity."""
        msg = GetVelocityMessage()
        return self._transceive_message(msg).velocity

    def set_status_led(self, led_index: StatusLed, status: bool) -> None:
        """Set the status of a status LED.

        Args:
            led_index: The index of the LED to set.
            status: The status to set the LED to (True for Green, False for Red)."""
        msg = SetStatusLedMessage(led_index.value, int(status))
        self._transceive_message(msg)

    def _transceive_message(self, req: RequestMessage) -> ResponseMessage:
        """Send a request message to the server and return the response message. Raises a RuntimeError on timeouts."""
        try:
            self._zmq_socket.send_pyobj(req)
            response = self._zmq_socket.recv_pyobj()
            if isinstance(response, ErrorResponse):
                raise KELORobileError(f"Error: {response.message} caused by {response.cause}")
            return response
        except zmq.Again:
            raise RuntimeError("Did not receive a reply in time from the tulip server. Is it running?")

    def close(self):
        """Close the connection to the server."""
        self._zmq_socket.close()
        self._zmq_ctx.term()

    def __del__(self):
        self.close()
