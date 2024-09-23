from dataclasses import dataclass

from airo_tulip.platform_driver import PlatformDriverType
from airo_tulip.structs import Attitude2DType


@dataclass
class RequestMessage:
    pass


@dataclass
class ResponseMessage:
    pass


@dataclass
class AreDrivesAlignedMessage(RequestMessage):
    pass


@dataclass
class SetPlatformVelocityTargetMessage(RequestMessage):
    vel_x: float
    vel_y: float
    vel_a: float
    timeout: float
    only_align_drives: bool


@dataclass
class SetDriverTypeMessage(RequestMessage):
    driver_type: PlatformDriverType


@dataclass
class StopServerMessage(RequestMessage):
    pass


@dataclass
class GetOdometryMessage(RequestMessage):
    pass

@dataclass
class ResetOdometryMessage(RequestMessage):
    pass

@dataclass
class OdometryResponse(ResponseMessage):
    odometry: Attitude2DType


@dataclass
class AreDrivesAlignedResponse(ResponseMessage):
    aligned: bool


@dataclass
class ErrorResponse(ResponseMessage):
    message: str
    cause: str


@dataclass
class OkResponse(ResponseMessage):
    pass
