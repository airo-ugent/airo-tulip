"""These messages are used to communicate between client (KELORobile) and server (TulipServer)."""

from dataclasses import dataclass
from typing import Final

from cyclonedds.idl import IdlStruct

TOPIC_RESET_ODOMETRY: Final[str] = "ResetOdometry"
TOPIC_SET_DRIVER_TYPE: Final[str] = "SetDriverType"
TOPIC_SET_TARGET_VELOCITY: Final[str] = "SetTargetVelocity"
TOPIC_VOLTAGE: Final[str] = "VoltageBus"
TOPIC_ODOMETRY: Final[str] = "Odometry"
TOPIC_VELOCITY: Final[str] = "Velocity"


@dataclass
class Velocity(IdlStruct, typename="Velocity.Msg"):
    """Velocity message."""
    timestamp: int
    x: float
    y: float
    a: float


@dataclass
class Odometry(IdlStruct, typename="Odometry.Msg"):
    """Odometry message."""
    timestamp: int
    x: float
    y: float
    a: float


@dataclass
class ResetOdometry(IdlStruct, typename="ResetOdometry.Msg"):
    """ResetOdometry message."""
    timestamp: int


@dataclass
class VoltageBus(IdlStruct, typename="VoltageBus.Msg"):
    """VoltageBus message."""
    timestamp: int
    voltage_bus: float


@dataclass
class SetDriverType(IdlStruct, typename="SetDriverType.Msg"):
    """SetDriverType message."""
    timestamp: int
    driver_type: int
