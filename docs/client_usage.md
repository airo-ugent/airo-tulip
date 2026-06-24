# Client usage (`airo-tulip`)

The `airo-tulip` package gives you the `KELORobile` client and the shared API types. You use it from your
own Python program to drive the robot and read its state over the network. This guide covers the full
public API.

For installation see [Getting started](getting_started.md). For running the server the client talks to,
see [Server usage](server_usage.md).

## Connecting

```python
from airo_tulip.api.client import KELORobile

client = KELORobile("10.10.129.21")   # the robot's IP; connects to the server on port 7447
```

Constructing `KELORobile` opens a Zenoh session, subscribes to the telemetry streams, starts a background
thread that streams the velocity setpoint, and performs a version handshake with the server. A failed
handshake (or an unreachable server) raises `KELORobileError`.

Useful constructor keyword arguments (all optional):

| Argument | Default | Meaning |
|---|---|---|
| `robot_port` | `7447` | Port to connect to. |
| `robot_id` | `"default"` | Namespace of the robot to talk to. Must match the server's `robot_id`. |
| `mode` | `"peer"` | `"peer"` connects directly to the server; `"client"` connects to a Zenoh router. |
| `publish_rate` | `20.0` | Rate (Hz) at which the current velocity setpoint is (re)published. |
| `query_timeout` | `2.0` | Timeout (s) for request/reply calls (handshake, set driver type, …). |

To talk to a robot whose server uses a router, or a non-default `robot_id`:

```python
client = KELORobile("10.10.129.21", mode="client", robot_id="robot_a")
```

## Driving the platform

The platform is commanded with a 2D velocity in the platform frame: `vx` forward, `vy` to the left
(both m/s), and `va` the angular velocity (rad/s).

```python
client.set_platform_velocity_target(0.2, 0.0, 0.0)                 # forward at 0.2 m/s
client.set_platform_velocity_target(0.0, 0.2, 0.0)                 # strafe left at 0.2 m/s
import math
client.set_platform_velocity_target(0.0, 0.0, math.pi / 8, timeout=2.0)  # rotate in place
```

### The setpoint times out — this is a safety feature

The velocity setpoint is **streamed** to the server, not sent once. Each call sets the current setpoint
and a client-side `timeout` (default `1.0` s); a background thread re-publishes it at `publish_rate` until
the timeout elapses, after which it **automatically reverts to zero** and the robot stops.

This means: **to keep driving, you must keep calling** `set_platform_velocity_target`. The pattern is a
control loop:

```python
import time

end = time.time() + 5.0
while time.time() < end:
    client.set_platform_velocity_target(0.2, 0.0, 0.0, timeout=0.5)
    time.sleep(0.1)
# loop exits -> setpoint expires within 0.5 s -> robot stops
```

The server has its own **watchdog**: if no command reaches it within its `watchdog_timeout` (default
`0.3` s, configured server-side), it stops the platform. So if your program crashes or the network drops,
the robot stops on its own.

### Velocity limits

The client validates every command and raises `ValueError` if it exceeds the safety limits (the server
additionally clamps incoming commands):

- linear: `MAX_PLATFORM_LINEAR_VELOCITY = 0.5` m/s (on the combined `vx`/`vy` magnitude)
- angular: `MAX_PLATFORM_ANGULAR_VELOCITY = π/4 ≈ 0.785` rad/s

```python
from airo_tulip.api.types import MAX_PLATFORM_LINEAR_VELOCITY, MAX_PLATFORM_ANGULAR_VELOCITY
```

The drives are strong; do not raise these limits unless you really know what you are doing (see
[How it works → Velocity limits](../airo-tulip/docs/how_it_works.md)).

## Aligning the drives

The drives steer (pivot) to point in the commanded direction before they can drive efficiently. You can
orient them without moving, which is useful before a fast or sharp manoeuvre:

```python
# Orient the drives for forward motion without driving.
client.align_drives(0.2, 0.0, 0.0)

# Or: align, wait until aligned, then drive — in one call.
ok = client.drive_aligned(0.2, 0.0, 0.0, timeout=1.0, align_timeout=5.0)
if not ok:
    print("drives did not align within 5 s")

# Check alignment yourself (from the status stream).
client.are_drives_aligned()   # -> bool
```

`drive_aligned` returns `True` if the drives aligned within `align_timeout` and driving started, `False`
otherwise.

## Driver modes: velocity and compliant

The platform driver has a velocity mode and three compliant modes. In a compliant mode the drives yield
to external forces (you can push the robot by hand), with increasing stiffness:

```python
from airo_tulip.api.types import PlatformDriverType

client.set_driver_type(PlatformDriverType.COMPLIANT_WEAK)      # most yielding
client.set_driver_type(PlatformDriverType.COMPLIANT_MODERATE)
client.set_driver_type(PlatformDriverType.COMPLIANT_STRONG)
client.set_driver_type(PlatformDriverType.VELOCITY)           # back to normal velocity control
```

`PlatformDriverType` values: `VELOCITY`, `COMPLIANT_WEAK`, `COMPLIANT_MODERATE`, `COMPLIANT_STRONG`.

## Reading state

Telemetry (odometry and platform status) is streamed from the server and cached locally; these reads
return the latest received value, they do not poll the robot.

```python
pose = client.get_odometry()   # np.ndarray [x, y, a]   (a measured from the X-axis)
twist = client.get_velocity()  # np.ndarray [vx, vy, va]
```

`get_odometry` / `get_velocity` wait up to `query_timeout` for the first telemetry sample and raise
`KELORobileError` if none arrives (the server is not running or not reachable).

> **Odometry caveat.** The default odometry is based on the drive encoders and is not always robust. For
> accurate localization, fuse in additional sensors (e.g. a compass or optical-flow sensor).

### Platform status and health

```python
state = client.get_status()    # PlatformState or None if nothing received yet
if state is not None:
    print(state.driver_state)          # str
    print(state.mode)                  # int (a PlatformDriverType value)
    print(state.drives_aligned)        # bool
    print(state.drives_enabled)        # bool
    print(state.watchdog_active)       # bool
    print(state.last_command_rejected) # None, or {reason, vx, vy, va} if the last command was clamped
    for d in state.drives:             # per-drive health
        print(d["index"], d["error"], d["temperature"], d["current"], d["voltage_bus"])
```

### Liveness

```python
client.is_alive()              # True if any telemetry arrived in the last 1.0 s
client.is_alive(max_age=0.5)   # custom window
```

## Drive power and odometry reset

```python
client.disable_drives()   # cut motor current to save energy (server keeps running)
client.enable_drives()    # re-energize the drives
client.reset_odometry()   # reset the estimated pose and velocity to zero
```

## Shutting down

```python
client.close()        # stop streaming commands and close the Zenoh session
client.stop_server()  # ask the remote server process to shut down (rarely needed)
```

Call `close()` when you are done with the client. `stop_server()` shuts the *server* down — normally the
server is a long-running systemd service you leave running, so use this only in scripted/standalone runs.

## Complete example

A minimal drive-and-stop program (adapted from
[`examples/velocity_mode.py`](../airo-tulip/examples/velocity_mode.py)):

```python
import math
import time

from airo_tulip.api.client import KELORobile


def main():
    client = KELORobile("10.10.129.21")

    client.set_platform_velocity_target(0.2, 0.0, 0.0)            # forward
    time.sleep(1)
    client.set_platform_velocity_target(0.0, 0.0, math.pi / 8, timeout=2.0)  # rotate
    time.sleep(2)
    client.set_platform_velocity_target(0.0, 0.0, 0.0)           # stop
    time.sleep(0.5)

    client.close()


if __name__ == "__main__":
    main()
```

A compliant-mode variant is in [`examples/compliant_mode.py`](../airo-tulip/examples/compliant_mode.py).

## API quick reference

| Method | Purpose |
|---|---|
| `set_platform_velocity_target(vx, vy, va, *, timeout=1.0)` | Stream a velocity setpoint (auto-stops after `timeout`). |
| `align_drives(vx, vy, va, *, timeout=1.0)` | Orient the drives without driving. |
| `drive_aligned(vx, vy, va, *, timeout=1.0, align_timeout=5.0)` | Align, wait, then drive. Returns `bool`. |
| `are_drives_aligned()` | Whether the drives are aligned with the last command. |
| `set_driver_type(PlatformDriverType)` | Switch between velocity and compliant modes. |
| `get_odometry()` | Latest estimated pose `[x, y, a]`. |
| `get_velocity()` | Latest estimated velocity `[vx, vy, va]`. |
| `get_status()` | Latest `PlatformState` (health, mode, alignment), or `None`. |
| `is_alive(max_age=1.0)` | Liveness: telemetry received within `max_age` seconds. |
| `enable_drives()` / `disable_drives()` | Energize / de-energize the motors. |
| `reset_odometry()` | Reset the estimated pose and velocity to zero. |
| `stop_server()` | Shut down the remote server process. |
| `close()` | Stop streaming and close the connection. |
