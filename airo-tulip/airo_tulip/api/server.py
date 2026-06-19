"""Compatibility shim.

The server (``TulipServer``) and the hardware abstraction layer moved to the separate
``airo-tulip-hal`` package, so that clients can install ``airo-tulip`` without the hardware
dependencies (notably ``pysoem``). This module exists only to give a clear error message to code
that still imports from the old location."""

raise ImportError(
    "TulipServer has moved to the 'airo-tulip-hal' package. "
    "Install it with `pip install airo-tulip-hal` and import from `airo_tulip_hal.server` instead, "
    "e.g. `from airo_tulip_hal.server import TulipServer, RobotConfiguration`."
)
