"""The KELORobile client interfaces with the TulipServer (see airo_tulip_hal.server) over Zenoh.

The velocity command is *streamed* to the server by a background thread (kept alive by the server's
watchdog); odometry and platform status are *streamed* from the server and cached locally; discrete
operations (handshake, set driver type, reset odometry, stop server) are request/reply (queryable)
calls."""

import math
import threading
import time
from typing import Optional
from uuid import uuid4

import numpy as np
from airo_tulip.api import codec
from airo_tulip.api.messages import (
    DisableDrivesRequest,
    EnableDrivesRequest,
    ErrorResponse,
    HandshakeRequest,
    HandshakeResponse,
    Odometry,
    PlatformState,
    ResetOdometryRequest,
    SetDriverTypeRequest,
    StopServerRequest,
    VelocityCommand,
)
from airo_tulip.api.transport import DEFAULT_ROUTER_PORT, Keys, open_session
from airo_tulip.api.types import (
    MAX_PLATFORM_ANGULAR_VELOCITY,
    MAX_PLATFORM_LINEAR_VELOCITY,
    Attitude2DType,
    PlatformDriverType,
)
from airo_typing import Vector3DType
from loguru import logger


class KELORobileError(RuntimeError):
    """Error raised when an error occurs in the KELORobile client."""


class KELORobile:
    """Client that interfaces with the TulipServer over Zenoh.

    Public methods preserve the previous API. Velocity commands are now streamed (fire-and-forget) with
    a client-side ``timeout`` that reverts the setpoint to zero; out-of-limit commands raise locally and
    are additionally clamped by the server. State reads (``get_odometry``, ``get_velocity``,
    ``are_drives_aligned``, ``get_status``) return the latest value from the telemetry stream."""

    def __init__(
        self,
        robot_ip: str,
        robot_port: int = DEFAULT_ROUTER_PORT,
        *,
        robot_id: str = "default",
        mode: str = "client",
        connect_endpoints: Optional[list] = None,
        listen_endpoints: Optional[list] = None,
        multicast: bool = False,
        publish_rate: float = 20.0,
        query_timeout: float = 2.0,
    ):
        """Initialize the client and connect to the server (via a Zenoh router by default).

        Args:
            robot_ip: Host of the Zenoh router to connect to.
            robot_port: Router port (default 7447).
            robot_id: Namespace of the robot to talk to.
            mode/connect_endpoints/listen_endpoints/multicast: advanced Zenoh session overrides.
            publish_rate: Rate (Hz) at which the current velocity setpoint is (re)published.
            query_timeout: Timeout (s) for request/reply calls."""
        self._keys = Keys(robot_id)
        self._query_timeout = query_timeout
        self._publish_period = 1.0 / publish_rate

        if connect_endpoints is None and mode == "client":
            connect_endpoints = [f"tcp/{robot_ip}:{robot_port}"]
        logger.info(f"Opening Zenoh session (mode={mode}, connect={connect_endpoints}).")
        self._session = open_session(mode, connect_endpoints, listen_endpoints, multicast)

        # Cached telemetry.
        self._lock = threading.Lock()
        self._latest_odometry: Optional[Odometry] = None
        self._latest_state: Optional[PlatformState] = None
        self._latest_odometry_time = 0.0
        self._latest_state_time = 0.0

        self._sub_odometry = self._session.declare_subscriber(self._keys.state_odometry, self._on_odometry)
        self._sub_state = self._session.declare_subscriber(self._keys.state_platform, self._on_state)

        # Streamed velocity setpoint state.
        self._setpoint = VelocityCommand(0.0, 0.0, 0.0, False)
        self._setpoint_expiry = 0.0
        self._pub_cmd = self._session.declare_publisher(self._keys.cmd_velocity)
        self._publisher_stop = threading.Event()
        self._publisher_thread = threading.Thread(target=self._publisher_loop, daemon=True)
        self._publisher_thread.start()

        logger.info("Performing handshake.")
        self._handshake()
        logger.info("Connection established!")

    # --- Telemetry subscribers ---

    def _on_odometry(self, sample) -> None:
        msg = codec.decode(sample.payload.to_bytes())
        with self._lock:
            self._latest_odometry = msg
            self._latest_odometry_time = time.time()

    def _on_state(self, sample) -> None:
        msg = codec.decode(sample.payload.to_bytes())
        with self._lock:
            self._latest_state = msg
            self._latest_state_time = time.time()

    # --- Streamed velocity setpoint ---

    def _publisher_loop(self) -> None:
        while not self._publisher_stop.is_set():
            with self._lock:
                if time.time() >= self._setpoint_expiry:
                    # The client-side timeout elapsed: revert to a zero setpoint (auto-stop).
                    self._setpoint = VelocityCommand(0.0, 0.0, 0.0, False)
                setpoint = self._setpoint
            self._pub_cmd.put(codec.encode(setpoint))
            self._publisher_stop.wait(self._publish_period)

    def _set_streamed_command(self, vel_x, vel_y, vel_a, timeout, only_align_drives) -> None:
        if math.sqrt(vel_x**2 + vel_y**2) > MAX_PLATFORM_LINEAR_VELOCITY:
            raise ValueError(f"Cannot set target linear velocity higher than {MAX_PLATFORM_LINEAR_VELOCITY} m/s")
        if abs(vel_a) > MAX_PLATFORM_ANGULAR_VELOCITY:
            raise ValueError(f"Cannot set target angular velocity higher than {MAX_PLATFORM_ANGULAR_VELOCITY} rad/s")
        if timeout < 0.0:
            raise ValueError("Cannot set negative timeout")
        with self._lock:
            self._setpoint = VelocityCommand(vel_x, vel_y, vel_a, only_align_drives)
            self._setpoint_expiry = time.time() + timeout

    def set_platform_velocity_target(
        self, vel_x: float, vel_y: float, vel_a: float, *, timeout: float = 1.0
    ) -> None:
        """Set the x, y and angular velocity of the platform.

        The setpoint is streamed to the server and automatically reverts to zero after ``timeout``
        seconds. Out-of-limit values raise a ValueError (the server additionally clamps).

        Args:
            vel_x: Linear velocity in x (forward), m/s.
            vel_y: Linear velocity in y (left), m/s.
            vel_a: Angular velocity, rad/s.
            timeout: Seconds after which the motion is automatically stopped (default 1.0)."""
        self._set_streamed_command(vel_x, vel_y, vel_a, timeout, only_align_drives=False)

    def align_drives(self, vel_x: float, vel_y: float, vel_a: float, *, timeout: float = 1.0) -> None:
        """Orient the drives for the given velocity without driving into that direction."""
        self._set_streamed_command(vel_x, vel_y, vel_a, timeout, only_align_drives=True)

    def drive_aligned(
        self, vel_x: float, vel_y: float, vel_a: float, *, timeout: float = 1.0, align_timeout: float = 5.0
    ) -> bool:
        """Align the drives for the given velocity, wait until aligned, then drive.

        Returns True if the drives aligned within ``align_timeout`` seconds and driving started."""
        self.align_drives(vel_x, vel_y, vel_a, timeout=align_timeout)
        deadline = time.time() + align_timeout
        while time.time() < deadline:
            if self.are_drives_aligned():
                self.set_platform_velocity_target(vel_x, vel_y, vel_a, timeout=timeout)
                return True
            time.sleep(self._publish_period)
        logger.warning("Drives did not align within the timeout.")
        return False

    # --- State reads (from the telemetry cache) ---

    def _await_odometry(self) -> Odometry:
        deadline = time.time() + self._query_timeout
        while time.time() < deadline:
            with self._lock:
                if self._latest_odometry is not None:
                    return self._latest_odometry
            time.sleep(0.02)
        raise KELORobileError("No odometry received from the server. Is it running?")

    def get_odometry(self) -> Attitude2DType:
        """Get the robot platform's latest estimated pose [x, y, a]."""
        return np.array(self._await_odometry().pose)

    def get_velocity(self) -> Vector3DType:
        """Get the robot platform's latest estimated velocity [vx, vy, va]."""
        return np.array(self._await_odometry().twist)

    def get_status(self) -> Optional[PlatformState]:
        """Get the latest platform status/health, or None if none received yet."""
        with self._lock:
            return self._latest_state

    def are_drives_aligned(self) -> bool:
        """Whether the drives are aligned with the last commanded velocity (from the status stream)."""
        with self._lock:
            return self._latest_state.drives_aligned if self._latest_state is not None else False

    def is_alive(self, max_age: float = 1.0) -> bool:
        """Whether telemetry has been received within ``max_age`` seconds (liveness / heartbeat)."""
        with self._lock:
            return (time.time() - max(self._latest_odometry_time, self._latest_state_time)) < max_age

    # --- Discrete operations (request/reply) ---

    def _query(self, key: str, request):
        replies = self._session.get(key, payload=codec.encode(request), timeout=self._query_timeout)
        for reply in replies:
            if reply.ok is not None:
                response = codec.decode(reply.ok.payload.to_bytes())
                if isinstance(response, ErrorResponse):
                    raise KELORobileError(f"Error: {response.message} caused by {response.cause}")
                return response
            raise KELORobileError(f"Server returned an error: {reply.err.payload.to_bytes()!r}")
        raise KELORobileError("Did not receive a reply in time from the tulip server. Is it running?")

    def _handshake(self) -> None:
        from importlib.metadata import version

        request = HandshakeRequest(str(uuid4()))
        reply = self._query(self._keys.srv_handshake, request)
        if not isinstance(reply, HandshakeResponse) or reply.uuid != request.uuid:
            raise KELORobileError("Handshake failed: server replied with an unexpected response.")
        client_version = version("airo-tulip")
        if client_version != reply.lib_version:
            raise KELORobileError(
                f"airo-tulip version mismatch: client is running {client_version}, "
                f"server is running {reply.lib_version}. Please ensure both match."
            )

    def set_driver_type(self, driver_type: PlatformDriverType) -> None:
        """Set the mode of the platform driver (velocity or compliant)."""
        self._query(self._keys.srv_set_driver_type, SetDriverTypeRequest(driver_type.value))

    def enable_drives(self) -> None:
        """Enable (re-energize) the drives."""
        self._query(self._keys.srv_enable_drives, EnableDrivesRequest())

    def disable_drives(self) -> None:
        """Disable the drives (cut motor current to save energy) while keeping the server running."""
        self._query(self._keys.srv_disable_drives, DisableDrivesRequest())

    def reset_odometry(self) -> None:
        """Reset the platform's odometry to 0."""
        self._query(self._keys.srv_reset_odometry, ResetOdometryRequest())

    def stop_server(self) -> None:
        """Stop the remote server process."""
        self._query(self._keys.srv_stop_server, StopServerRequest())

    def close(self) -> None:
        """Stop streaming commands and close the connection to the server."""
        self._publisher_stop.set()
        if self._publisher_thread.is_alive():
            self._publisher_thread.join(timeout=1.0)
        self._session.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
