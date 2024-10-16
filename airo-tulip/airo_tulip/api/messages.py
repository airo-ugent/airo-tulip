"""These messages are used to communicate between client (KELORobile) and server (TulipServer)."""

from dataclasses import dataclass

from airo_tulip.hardware.platform_driver import PlatformDriverType
from airo_tulip.hardware.structs import Attitude2DType
from rerun.components import Vector3DType


@dataclass
class RequestMessage:
    """Base class for all request messages."""
    pass


@dataclass
class ResponseMessage:
    """Base class for all response messages."""
    pass


@dataclass
class HandshakeMessage:
    """A handshake message is used to establish a connection between client and server."""
    uuid: str


@dataclass
class HandshakeResponse:
    """A handshake reply is used to confirm a connection between client and server."""
    uuid: str


@dataclass
class AreDrivesAlignedMessage(RequestMessage):
    """A message to check if the drives are aligned."""
    pass


@dataclass
class SetPlatformVelocityTargetMessage(RequestMessage):
    """A message to set the platform velocity target."""
    vel_x: float
    vel_y: float
    vel_a: float
    timeout: float
    only_align_drives: bool


@dataclass
class MovePlatformToPoseMessage(RequestMessage):
    """A message to move the platform to a specific pose."""
    x: float
    y: float
    a: float
    timeout: float


@dataclass
class StopPositionControlLoopMessage(RequestMessage):
    """A message to stop the position control loop immediately."""
    pass


@dataclass
class SetDriverTypeMessage(RequestMessage):
    """A message to set the driver type (velocity mode or compliant mode)."""
    driver_type: PlatformDriverType


@dataclass
class StopServerMessage(RequestMessage):
    """A message to stop the server."""
    pass


@dataclass
class GetVelocityMessage(RequestMessage):
    """A message to get the velocity of the robot."""
    pass


@dataclass
class GetOdometryMessage(RequestMessage):
    """A message to get the odometry of the robot."""
    pass


@dataclass
class ResetOdometryMessage(RequestMessage):
    """A message to reset the odometry of the robot."""
    pass


@dataclass
class OdometryResponse(ResponseMessage):
    """A response message containing the odometry of the robot."""
    odometry: Attitude2DType


@dataclass
class VelocityResponse(ResponseMessage):
    """A response message containing the velocity of the robot."""
    velocity: Vector3DType


@dataclass
class AreDrivesAlignedResponse(ResponseMessage):
    """A response message containing the alignment status of the drives."""
    aligned: bool


@dataclass
class ErrorResponse(ResponseMessage):
    """A response message containing an error message."""
    message: str
    cause: str


@dataclass
class ConcurrencyExceptionResponse(ResponseMessage):
    """A response indicating that a request was made which is invalid in the current robot state, because another
    thread is controlling the robot. You can expect this response when the robot is executing a position control
    loop and another request to move the robot is made."""
    pass


@dataclass
class OkResponse(ResponseMessage):
    """A response message indicating that the request was successful."""
    pass
