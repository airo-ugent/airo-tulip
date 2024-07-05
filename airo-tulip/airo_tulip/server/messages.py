from dataclasses import dataclass


@dataclass
class RequestMessage:
    pass


@dataclass
class ResponseMessage:
    pass


@dataclass
class SetPlatformVelocityTargetMessage(RequestMessage):
    vel_x: float
    vel_y: float
    vel_a: float
    timeout: float


@dataclass
class StopServerMessage(RequestMessage):
    pass


@dataclass
class ErrorResponse(ResponseMessage):
    message: str
    cause: str


@dataclass
class OkResponse(ResponseMessage):
    pass
