"""Zenoh session setup and key-expression helpers shared by the client and server.

The default deployment is **peer**-to-peer: the server listens and the client connects directly to it,
with no Zenoh router (`zenohd`) in between. Multicast discovery is disabled, so endpoints are given
explicitly. The session knobs are overridable to instead run in **client** mode against a router (e.g.
to fan out to many clients or bridge subnets) or for tests."""

import json
from typing import List, Optional

import zenoh

DEFAULT_PORT = 7447
# Backwards-compatible alias: the same port is used whether peering directly or via a router.
DEFAULT_ROUTER_PORT = DEFAULT_PORT


def open_session(
    mode: str = "peer",
    connect_endpoints: Optional[List[str]] = None,
    listen_endpoints: Optional[List[str]] = None,
    multicast: bool = False,
) -> zenoh.Session:
    """Open a Zenoh session.

    Args:
        mode: Zenoh mode, "peer" (connect directly to another peer) or "client" (connect to a router).
        connect_endpoints: Endpoints to connect to, e.g. ["tcp/10.10.0.1:7447"].
        listen_endpoints: Endpoints to listen on (peer mode).
        multicast: Whether to enable multicast scouting (disabled by default; we use explicit endpoints)."""
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
