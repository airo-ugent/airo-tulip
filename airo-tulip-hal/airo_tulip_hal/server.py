"""The TulipServer exposes the KELO Robile platform over Zenoh.

Communication model (ROS 2-style):

- It *subscribes* to a streamed velocity setpoint (`cmd/velocity`) and applies the latest one. A
  watchdog stops the platform if no command arrives within ``watchdog_timeout`` seconds.
- It *publishes* odometry (`state/odometry`) and platform status/health (`state/status`) at the
  EtherCAT loop rate.
- It answers *queryable* (request/reply) calls for discrete operations: handshake, set driver type,
  reset odometry, stop server.

By default it connects in client mode to a Zenoh router (typically running on the KELO CPU brick)."""

import math
import time
from threading import Event, Lock, Thread
from typing import List, Optional

from airo_tulip.api import codec
from airo_tulip.api.messages import (
    ErrorResponse,
    HandshakeRequest,
    HandshakeResponse,
    Odometry,
    OkResponse,
    PlatformState,
    SetDriverTypeRequest,
    VelocityCommand,
)
from airo_tulip.api.transport import DEFAULT_ROUTER_PORT, Keys, open_session
from airo_tulip.api.types import PlatformDriverType
from airo_tulip_hal.hardware.constants import MAX_PLATFORM_LINEAR_VELOCITY, MAX_PLATFORM_ANGULAR_VELOCITY
from airo_tulip_hal.hardware.ethercat import (
    STAT1_OVERCURRENT_1,
    STAT1_OVERCURRENT_2,
    STAT1_OVERTEMP_1,
    STAT1_OVERTEMP_2,
    STAT1_OVERVOLTAGE,
    STAT1_UNDERVOLTAGE,
)
from airo_tulip_hal.hardware.robile_platform import RobilePlatform
from airo_tulip_hal.hardware.structs import WheelConfig
from loguru import logger

# Bitmask of status1 flags that indicate a drive fault.
_DRIVE_ERROR_MASK = (
    STAT1_UNDERVOLTAGE
    | STAT1_OVERVOLTAGE
    | STAT1_OVERCURRENT_1
    | STAT1_OVERCURRENT_2
    | STAT1_OVERTEMP_1
    | STAT1_OVERTEMP_2
)


class RobotConfiguration:
    """The mobile robot configuration: an EtherCAT device string and a list of wheel configurations.

    This is required to properly set up the platform and should be passed to the TulipServer's constructor."""

    def __init__(self, ecat_device: str, wheel_configs: List[WheelConfig]):
        self.ecat_device = ecat_device
        self.wheel_configs = wheel_configs


class TulipServer:
    """Exposes the KELO Robile platform over Zenoh. See module docstring for the communication model."""

    def __init__(
        self,
        robot_configuration: RobotConfiguration,
        *,
        robot_id: str = "default",
        router_endpoint: Optional[str] = None,
        mode: str = "client",
        connect_endpoints: Optional[List[str]] = None,
        listen_endpoints: Optional[List[str]] = None,
        multicast: bool = False,
        loop_frequency: float = 20.0,
        watchdog_timeout: float = 0.3,
    ):
        """Initialize the server.

        Args:
            robot_configuration: The robot configuration.
            robot_id: Namespace for this robot's Zenoh key expressions.
            router_endpoint: Zenoh router endpoint to connect to (default: tcp/127.0.0.1:7447).
            mode: Zenoh mode ("client" to use a router, or "peer").
            connect_endpoints/listen_endpoints/multicast: advanced Zenoh session overrides.
            loop_frequency: EtherCAT loop frequency (Hz).
            watchdog_timeout: Stop the platform if no velocity command arrives within this many seconds."""
        self._keys = Keys(robot_id)
        self._robot_id = robot_id
        self._loop_frequency = loop_frequency
        self._watchdog_timeout = watchdog_timeout

        # Velocity-command / watchdog state, shared between the Zenoh subscriber callback and the
        # EtherCAT loop.
        self._cmd_lock = Lock()
        self._last_command_time = 0.0
        self._last_command_rejected: Optional[dict] = None

        self._should_stop = Event()

        # Zenoh session.
        if connect_endpoints is None and mode == "client":
            endpoint = router_endpoint or f"tcp/127.0.0.1:{DEFAULT_ROUTER_PORT}"
            connect_endpoints = [endpoint]
        logger.info(f"Opening Zenoh session (mode={mode}, connect={connect_endpoints}, listen={listen_endpoints}).")
        self._session = open_session(mode, connect_endpoints, listen_endpoints, multicast)

        # Robot platform.
        self._platform = RobilePlatform(
            robot_configuration.ecat_device, robot_configuration.wheel_configs, PlatformDriverType.VELOCITY
        )
        if not self._platform.init_ethercat():
            raise RuntimeError("Failed to initialise EtherCAT: not all slaves reached an operational state.")

        # Declare publishers, subscriber and queryables.
        self._pub_odometry = self._session.declare_publisher(self._keys.state_odometry)
        self._pub_state = self._session.declare_publisher(self._keys.state_platform)
        self._sub_cmd = self._session.declare_subscriber(self._keys.cmd_velocity, self._on_velocity_command)
        self._queryables = [
            self._session.declare_queryable(self._keys.srv_handshake, self._guard(self._on_handshake)),
            self._session.declare_queryable(self._keys.srv_set_driver_type, self._guard(self._on_set_driver_type)),
            self._session.declare_queryable(self._keys.srv_enable_drives, self._guard(self._on_enable_drives)),
            self._session.declare_queryable(self._keys.srv_disable_drives, self._guard(self._on_disable_drives)),
            self._session.declare_queryable(self._keys.srv_reset_odometry, self._guard(self._on_reset_odometry)),
            self._session.declare_queryable(self._keys.srv_stop_server, self._guard(self._on_stop_server)),
        ]

    # --- Streamed command handling ---

    def _on_velocity_command(self, sample) -> None:
        """Apply an incoming streamed velocity setpoint, clamping it to the safety limits."""
        try:
            cmd = codec.decode(sample.payload.to_bytes())
        except Exception:
            logger.exception("Failed to decode velocity command.")
            return
        if not isinstance(cmd, VelocityCommand):
            logger.warning(f"Ignoring unexpected message on the command stream: {type(cmd).__name__}.")
            return

        vx, vy, va, rejected = self._clamp_velocity(cmd.vx, cmd.vy, cmd.va)
        with self._cmd_lock:
            self._last_command_time = time.time()
            # Latch the most recent rejection (with a timestamp) rather than clearing it on the next
            # valid command, so a clamped command stays observable to clients polling status at any rate.
            if rejected is not None:
                rejected["stamp_ns"] = time.time_ns()
                self._last_command_rejected = rejected
        # The driver's per-target timeout doubles as the watchdog: each command refreshes it.
        self._platform.driver.set_platform_velocity_target(
            vx, vy, va, timeout=self._watchdog_timeout, only_align_drives=cmd.only_align_drives
        )

    def _clamp_velocity(self, vx: float, vy: float, va: float):
        """Clamp a velocity setpoint to the platform safety limits. Returns (vx, vy, va, rejected_info)."""
        rejected = None
        linear = math.hypot(vx, vy)
        if linear > MAX_PLATFORM_LINEAR_VELOCITY:
            scale = MAX_PLATFORM_LINEAR_VELOCITY / linear
            rejected = {"reason": "linear velocity exceeded limit", "vx": vx, "vy": vy, "va": va}
            vx, vy = vx * scale, vy * scale
        if abs(va) > MAX_PLATFORM_ANGULAR_VELOCITY:
            rejected = {"reason": "angular velocity exceeded limit", "vx": vx, "vy": vy, "va": va}
            va = math.copysign(MAX_PLATFORM_ANGULAR_VELOCITY, va)
        return vx, vy, va, rejected

    # --- Telemetry ---

    def _publish_telemetry(self) -> None:
        """Publish odometry and platform status from the current monitor/driver state."""
        monitor = self._platform.monitor
        driver = self._platform.driver
        stamp_ns = time.time_ns()

        pose = monitor.get_estimated_robot_pose()
        twist = monitor.get_estimated_velocity()
        self._pub_odometry.put(
            codec.encode(Odometry(stamp_ns=stamp_ns, pose=[float(v) for v in pose], twist=[float(v) for v in twist]))
        )

        drives = []
        for i in range(monitor.num_wheels):
            status1 = int(monitor.get_status1(i))
            drives.append(
                {
                    "index": i,
                    "error": bool(status1 & _DRIVE_ERROR_MASK),
                    "status1": status1,
                    "status2": int(monitor.get_status2(i)),
                    "temperature": float(monitor.get_temperature(i)[2]),
                    "current": float(monitor.get_current_in(i)),
                    "voltage_bus": float(monitor.get_voltage_bus(i)),
                }
            )

        with self._cmd_lock:
            last_rejected = self._last_command_rejected
            watchdog_active = (time.time() - self._last_command_time) < self._watchdog_timeout

        self._pub_state.put(
            codec.encode(
                PlatformState(
                    stamp_ns=stamp_ns,
                    driver_state=driver.state.name,
                    mode=driver.driver_type.value,
                    drives_aligned=driver.are_drives_aligned(read_only=True),
                    drives_enabled=driver.drives_enabled,
                    watchdog_active=watchdog_active,
                    last_command_rejected=last_rejected,
                    drives=drives,
                )
            )
        )

    # --- EtherCAT loop ---

    def _ethercat_loop(self) -> None:
        desired_duration = int((1 / self._loop_frequency) * 1e9)
        while not self._should_stop.is_set():
            start_ns = time.time_ns()
            ok = self._platform.step()
            if not ok:
                logger.error("Platform reported a failure during step; stopping the server.")
                self._should_stop.set()
                break

            try:
                self._publish_telemetry()
            except Exception:
                logger.exception("Failed to publish telemetry.")

            actual_duration = time.time_ns() - start_ns
            if actual_duration < desired_duration:
                time.sleep((desired_duration - actual_duration) * 1e-9)
            else:
                logger.warning(
                    f"EtherCAT loop overran its period: took {actual_duration * 1e-6:.1f} ms, "
                    f"budget {desired_duration * 1e-6:.1f} ms."
                )

    def run(self) -> None:
        """Run the server until stopped (via a stop-server request or KeyboardInterrupt)."""
        logger.info("Starting EtherCAT loop and listening for requests.")
        thread = Thread(target=self._ethercat_loop, daemon=True)
        thread.start()
        try:
            thread.join()
        except KeyboardInterrupt:
            self._should_stop.set()
            thread.join(timeout=2.0)
        finally:
            self._session.close()
            logger.info("Server stopped.")

    # --- Queryable handlers ---

    def _guard(self, handler):
        """Wrap a queryable handler so that any failure is reported back to the client as an error reply
        instead of being swallowed (which would leave the client waiting until its timeout)."""

        def wrapped(query):
            try:
                handler(query)
            except Exception as e:
                logger.exception(f"Error handling query on {query.key_expr}.")
                try:
                    query.reply_err(f"{type(e).__name__}: {e}")
                except Exception:
                    logger.exception("Failed to send error reply.")

        return wrapped

    def _reply(self, query, response) -> None:
        query.reply(query.key_expr, codec.encode(response))

    def _on_handshake(self, query) -> None:
        from importlib.metadata import version

        request = codec.decode(query.payload.to_bytes())
        if not isinstance(request, HandshakeRequest):
            raise ValueError(f"Expected a HandshakeRequest, got {type(request).__name__}.")
        logger.info("Handling handshake request.")
        self._reply(query, HandshakeResponse(request.uuid, version("airo-tulip"), self._robot_id))

    def _on_set_driver_type(self, query) -> None:
        request = codec.decode(query.payload.to_bytes())
        if not isinstance(request, SetDriverTypeRequest):
            raise ValueError(f"Expected a SetDriverTypeRequest, got {type(request).__name__}.")
        self._platform.driver.set_driver_type(PlatformDriverType(request.driver_type))
        self._reply(query, OkResponse())

    def _on_enable_drives(self, query) -> None:
        codec.decode(query.payload.to_bytes())  # EnableDrivesRequest
        logger.info("Enabling drives.")
        self._platform.driver.set_drives_enabled(True)
        self._reply(query, OkResponse())

    def _on_disable_drives(self, query) -> None:
        codec.decode(query.payload.to_bytes())  # DisableDrivesRequest
        logger.info("Disabling drives (motors de-energized to save energy).")
        self._platform.driver.set_drives_enabled(False)
        self._reply(query, OkResponse())

    def _on_reset_odometry(self, query) -> None:
        codec.decode(query.payload.to_bytes())  # ResetOdometryRequest
        self._platform.monitor.reset_odometry()
        self._reply(query, OkResponse())

    def _on_stop_server(self, query) -> None:
        codec.decode(query.payload.to_bytes())  # StopServerRequest
        logger.info("Received stop request.")
        self._reply(query, OkResponse())
        self._should_stop.set()
