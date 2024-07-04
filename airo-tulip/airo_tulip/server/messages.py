from dataclasses import dataclass


@dataclass
class SetPlatformVelocityTargetMessage:
    vel_x: float
    vel_y: float
    vel_a: float

@dataclass
class ErrorResponse:
    message: str
    cause: str

@dataclass
class OkResponse:
    pass