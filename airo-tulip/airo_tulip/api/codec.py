"""msgpack-based (de)serialization for the wire messages in ``messages.py``.

This replaces the previous pickle-based transport (``send_pyobj``/``recv_pyobj``), which allowed
arbitrary code execution from anything that could reach the server. msgpack is compact (good for the
20 Hz telemetry streams), fast, and language-agnostic.

Each encoded payload is a msgpack map ``{"t": <type name>, "d": <fields>}``. Because every message
field is a primitive / list / dict, ``dataclasses.asdict`` + ``cls(**d)`` round-trips losslessly."""

import dataclasses

import msgpack

from airo_tulip.api import messages

_MESSAGE_TYPES = [
    messages.VelocityCommand,
    messages.Odometry,
    messages.PlatformState,
    messages.HandshakeRequest,
    messages.HandshakeResponse,
    messages.SetDriverTypeRequest,
    messages.ResetOdometryRequest,
    messages.StopServerRequest,
    messages.OkResponse,
    messages.ErrorResponse,
]
_REGISTRY = {cls.__name__: cls for cls in _MESSAGE_TYPES}


def encode(message) -> bytes:
    """Serialize a message dataclass to msgpack bytes."""
    type_name = type(message).__name__
    if type_name not in _REGISTRY:
        raise ValueError(f"Cannot encode unknown message type: {type_name}")
    return msgpack.packb({"t": type_name, "d": dataclasses.asdict(message)}, use_bin_type=True)


def decode(data: bytes):
    """Deserialize msgpack bytes back into a message dataclass."""
    obj = msgpack.unpackb(data, raw=False)
    type_name = obj.get("t")
    cls = _REGISTRY.get(type_name)
    if cls is None:
        raise ValueError(f"Cannot decode unknown message type: {type_name!r}")
    return cls(**obj["d"])
