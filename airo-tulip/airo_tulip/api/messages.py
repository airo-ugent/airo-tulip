"""Wire messages exchanged between the client (KELORobile) and server (TulipServer).

All fields are primitives / lists / dicts so they serialize cleanly with msgpack (see ``codec.py``).
Rich types (numpy arrays, ``PlatformDriverType``) are converted at the client/server boundary, not on
the wire.

The communication model (see ``docs/how_it_works.md``):

- ``VelocityCommand`` is *streamed* from client to server (pub/sub) and kept alive by a watchdog.
- ``Odometry`` and ``PlatformState`` are *streamed* from server to client (pub/sub).
- The remaining request/response pairs are *queryable* (request/reply) calls for discrete operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# --- Streamed command: client -> server (pub/sub) ---


@dataclass
class VelocityCommand:
    """A platform velocity setpoint. Streamed at a fixed rate; the server stops the platform if no
    command arrives within its watchdog timeout."""

    vx: float
    vy: float
    va: float
    only_align_drives: bool = False


# --- Streamed telemetry: server -> client (pub/sub) ---


@dataclass
class Odometry:
    """Estimated platform odometry. ``pose`` is [x, y, a] and ``twist`` is [vx, vy, va]."""

    stamp_ns: int
    pose: List[float]
    twist: List[float]


@dataclass
class PlatformState:
    """Continuously published platform status / health.

    ``drives`` is a list of per-drive dicts with keys:
    ``index``, ``error`` (bool), ``status1``, ``status2`` (ints), ``temperature``, ``current``,
    ``voltage_bus`` (floats).
    ``last_command_rejected`` is ``None`` or a dict ``{reason, vx, vy, va}`` describing the most recent
    command that was clamped to the safety limits."""

    stamp_ns: int
    driver_state: str
    mode: int  # PlatformDriverType value
    drives_aligned: bool
    watchdog_active: bool
    last_command_rejected: Optional[dict]
    drives: List[dict] = field(default_factory=list)


# --- Request/reply: queryable (discrete operations) ---


@dataclass
class HandshakeRequest:
    """Sent by the client on connect to verify the server is reachable and version-compatible."""

    uuid: str


@dataclass
class HandshakeResponse:
    uuid: str
    lib_version: str
    robot_id: str


@dataclass
class SetDriverTypeRequest:
    """Set the platform driver mode (velocity or compliant). ``driver_type`` is a PlatformDriverType value."""

    driver_type: int


@dataclass
class ResetOdometryRequest:
    """Reset the platform's estimated pose and velocity to zero."""


@dataclass
class StopServerRequest:
    """Request the server to shut down."""


@dataclass
class OkResponse:
    """Indicates a request was handled successfully."""


@dataclass
class ErrorResponse:
    """Indicates a request failed."""

    message: str
    cause: str
