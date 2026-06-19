"""Zenoh session setup and key-expression helpers shared by the client and server.

The default deployment connects in **client** mode to a Zenoh **router** (`zenohd`), avoiding multicast
discovery. The router typically runs on the KELO CPU brick. The session knobs are overridable (e.g. to
run a peer-to-peer setup or for tests)."""

import json
from typing import List, Optional

import zenoh

DEFAULT_ROUTER_PORT = 7447


def open_session(
    mode: str = "client",
    connect_endpoints: Optional[List[str]] = None,
    listen_endpoints: Optional[List[str]] = None,
    multicast: bool = False,
) -> zenoh.Session:
    """Open a Zenoh session.

    Args:
        mode: Zenoh mode, "client" (connect to a router) or "peer".
        connect_endpoints: Endpoints to connect to, e.g. ["tcp/10.10.0.1:7447"].
        listen_endpoints: Endpoints to listen on (peer mode).
        multicast: Whether to enable multicast scouting (disabled by default; we rely on a router)."""
    config = zenoh.Config()
    config.insert_json5("mode", json.dumps(mode))
    if connect_endpoints:
        config.insert_json5("connect/endpoints", json.dumps(connect_endpoints))
    if listen_endpoints:
        config.insert_json5("listen/endpoints", json.dumps(listen_endpoints))
    config.insert_json5("scouting/multicast/enabled", json.dumps(multicast))
    return zenoh.open(config)


class Keys:
    """Key-expression builder for a robot, namespaced by ``robot_id``."""

    def __init__(self, robot_id: str = "default"):
        self._base = f"airo_tulip/{robot_id}"

    @property
    def cmd_velocity(self) -> str:
        return f"{self._base}/cmd/velocity"

    @property
    def state_odometry(self) -> str:
        return f"{self._base}/state/odometry"

    @property
    def state_platform(self) -> str:
        return f"{self._base}/state/status"

    @property
    def srv_handshake(self) -> str:
        return f"{self._base}/srv/handshake"

    @property
    def srv_set_driver_type(self) -> str:
        return f"{self._base}/srv/set_driver_type"

    @property
    def srv_enable_drives(self) -> str:
        return f"{self._base}/srv/enable_drives"

    @property
    def srv_disable_drives(self) -> str:
        return f"{self._base}/srv/disable_drives"

    @property
    def srv_reset_odometry(self) -> str:
        return f"{self._base}/srv/reset_odometry"

    @property
    def srv_stop_server(self) -> str:
        return f"{self._base}/srv/stop_server"
