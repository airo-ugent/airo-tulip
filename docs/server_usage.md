# Server usage (`airo-tulip-hal`)

The `airo-tulip-hal` package is the hardware abstraction layer for the KELO Robile platform. It contains
the EtherCAT driver, the platform monitor and controllers, and the `TulipServer` that exposes the
platform over the network. **It runs on the KELO CPU brick**, because it needs raw-socket EtherCAT access
to the drives.

This guide covers running and configuring the server. To control the running server, see
[Client usage](client_usage.md).

## How the server is normally run

On a production brick the server is a **systemd service**, installed by `install.sh`:

- the service `tulip` runs `airo-tulip-server --config /etc/airo-tulip/robot.yaml` on boot,
- it runs as root (EtherCAT needs raw-socket access),
- it listens for direct (peer) client connections on port `7447`.

You manage it with the usual systemd commands:

```bash
sudo systemctl status tulip      # is the server running?
journalctl -u tulip -f           # follow the logs
sudo systemctl restart tulip     # apply configuration changes
sudo systemctl stop tulip        # stop the server
```

Installing, updating, and uninstalling the service are documented in the repository
[`README.md`](../README.md).

## Running the server by hand

The systemd service simply runs the `airo-tulip-server` console script. You can run it yourself — useful
during development, or to watch the logs in the foreground:

```bash
airo-tulip-server --config robot.yaml
```

The server runs until it is stopped with a stop-server request from a client or with `Ctrl-C`.

> If a production install is active, stop it first (`sudo systemctl stop tulip`) so the two servers don't
> contend for the EtherCAT bus.

For a development checkout (from the repository root), run it through `uv` without installing system-wide:

```bash
cp deploy/robot.example.yaml robot.yaml   # then edit for your platform (git-ignored)
uv run airo-tulip-server --config robot.yaml
```

## The configuration file

The server is configured by a YAML file describing your platform. The drive layout and EtherCAT device
are specific to each robot and come from KELO with your platform. A fully documented template is
[`deploy/robot.example.yaml`](../deploy/robot.example.yaml):

```yaml
# EtherCAT device the KELO drives are connected to (platform-specific).
ethercat_device: eno1

# Drive layout. Each entry is one drive: its EtherCAT slave number and its (x, y) position and mounting
# angle (a) relative to the platform centre.
wheels:
  - { ethercat_number: 3, x: 0.233,  y: 0.1165,  a: 1.57 }
  - { ethercat_number: 5, x: 0.233,  y: -0.1165, a: 1.57 }
  - { ethercat_number: 7, x: -0.233, y: -0.1165, a: -1.57 }
  - { ethercat_number: 9, x: -0.233, y: 0.1165,  a: 1.57 }

# Optional settings (defaults shown).
robot_id: default          # Zenoh key-expression namespace for this robot.
loop_frequency: 20.0       # EtherCAT loop frequency in Hz.
watchdog_timeout: 0.3      # Stop the platform if no velocity command arrives within this many seconds.

# Connectivity. Uncomment to route through a Zenoh router instead of peer mode:
# mode: client
# router_endpoint: tcp/127.0.0.1:7447
```

### Required keys

| Key | Meaning |
|---|---|
| `ethercat_device` | The network interface the KELO drives are on (e.g. `eno1`). |
| `wheels` | A list of drives. Each entry needs `ethercat_number` (EtherCAT slave id) and `x`, `y`, `a` (the drive's position in metres and mounting angle in radians relative to the platform centre). At least one is required. |

### Optional keys

These map directly onto `TulipServer` keyword arguments; omit them to use the defaults shown above.

| Key | Default | Meaning |
|---|---|---|
| `robot_id` | `default` | Namespace for this robot. Clients must use the same `robot_id` to talk to it. |
| `mode` | `peer` | `peer` listens for direct client connections; `client` connects to a Zenoh router. |
| `router_endpoint` | `tcp/127.0.0.1:7447` | Router to connect to in client mode. Ignored in peer mode. |
| `loop_frequency` | `20.0` | EtherCAT loop frequency in Hz. The drives must be serviced often enough to stay enabled; 20 Hz is the recommended rate. |
| `watchdog_timeout` | `0.3` | Stop the platform if no velocity command arrives within this many seconds. |

After editing the config, restart the server (`sudo systemctl restart tulip`, or restart your foreground
process) for the changes to take effect.

## Peer mode vs. router mode

By default the server runs in Zenoh **peer** mode: it listens on `tcp/0.0.0.0:7447` and clients connect
to it directly. No Zenoh router is needed. This is the right choice for most setups.

For setups with many clients, or that span subnets, you can instead run a Zenoh router (`zenohd`,
available from the [zenoh releases](https://github.com/eclipse-zenoh/zenoh/releases)) and have both the
server and the clients connect to it in `client` mode:

- server: set `mode: client` (and optionally `router_endpoint`) in the config,
- client: construct `KELORobile(router_ip, mode="client")`.

## Embedding the server in your own program

If you would rather not use the console script, construct and run a `TulipServer` directly. This is what
the CLI does under the hood.

```python
from airo_tulip_hal.server import RobotConfiguration, TulipServer
from airo_tulip_hal.hardware.structs import WheelConfig

config = RobotConfiguration(
    ecat_device="eno1",
    wheel_configs=[
        WheelConfig(ethercat_number=3, x=0.233,  y=0.1165,  a=1.57),
        WheelConfig(ethercat_number=5, x=0.233,  y=-0.1165, a=1.57),
        WheelConfig(ethercat_number=7, x=-0.233, y=-0.1165, a=-1.57),
        WheelConfig(ethercat_number=9, x=-0.233, y=0.1165,  a=1.57),
    ],
)

server = TulipServer(config, robot_id="default", loop_frequency=20.0, watchdog_timeout=0.3)
server.run()   # blocks until a stop-server request or KeyboardInterrupt
```

`TulipServer` initializes EtherCAT in its constructor and raises `RuntimeError` if the drives do not reach
an operational state — so this must run on the brick with the drives connected.

## Lower-level hardware access

Behind the server, `RobilePlatform` coordinates EtherCAT and exposes a `driver` (sends wheel setpoints)
and a `monitor` (reads odometry and per-drive health). You normally don't touch these directly — the
server drives them — but they are documented in
[`how_it_works.md`](../airo-tulip/docs/how_it_works.md) if you need to extend the hardware layer.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Failed to initialise EtherCAT` on startup | Wrong `ethercat_device`, drives not powered, or another process (e.g. the `tulip` service) is already on the bus. Check `ethercat_device` and `sudo systemctl stop tulip`. |
| Client handshake fails with a version mismatch | The client and server `airo-tulip` versions differ. Install matching versions on both sides. |
| Robot won't move / stops immediately | The watchdog is stopping it because commands aren't arriving fast enough. The client must stream `set_platform_velocity_target` repeatedly (see [Client usage](client_usage.md)). |
| Client can't connect | Check the robot IP/port, that `robot_id` matches, and that the server is running (`systemctl status tulip`). |
| Drives don't drive but pivot | They may be in a compliant mode. Set `PlatformDriverType.VELOCITY`, and check `get_status()` health flags. |
