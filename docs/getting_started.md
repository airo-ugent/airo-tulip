# Getting started

This guide takes you from nothing to driving a KELO Robile platform: install the server on the brick,
install the client on your machine, connect, and send your first velocity command.

It assumes the platform's hardware and network have already been set up (see
[`kelo_setup.md`](../airo-tulip/docs/kelo_setup.md)). If you are setting up a brand-new platform, read
that first.

## 1. Install the server on the KELO CPU brick

The server (`airo-tulip-hal`) runs on the KELO CPU brick and is installed from source with `install.sh`.
On a brick that already shipped with our software, this is usually already done.

```bash
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
./install.sh
```

`install.sh` builds the packages into `/opt/airo-tulip`, installs an `airo-tulip-server` console script,
seeds a configuration file at `/etc/airo-tulip/robot.yaml`, and registers a `tulip` systemd service that
starts the server on boot. See the repository [`README.md`](../README.md) for the full details, including
prerequisites, updating, and uninstalling.

**Configure your platform before driving.** The drive layout and EtherCAT device are specific to each
robot, so edit `/etc/airo-tulip/robot.yaml` (the values come from KELO with your platform), then restart:

```bash
sudo systemctl restart tulip
```

Check that the server is running and watch its logs:

```bash
sudo systemctl status tulip      # is the server running?
journalctl -u tulip -f           # follow the server logs
```

See [Server usage](server_usage.md) for the configuration format and for running the server by hand
(e.g. during development).

## 2. Install the client on your machine

The client (`airo-tulip`) installs from PyPI on any machine on the same network as the robot. It requires
Python 3.9 or newer and does **not** depend on any hardware libraries.

```bash
pip install airo-tulip
```

> The client and server must run the **same `airo-tulip` version**. If you installed a specific version
> on the brick, pin the client to match: `pip install airo-tulip==<version>`.

## 3. Connect and drive

Find the robot's IP address on your network (e.g. `10.10.129.21`), then:

```python
from airo_tulip.api.client import KELORobile

kelo_ip = "10.10.129.21"
client = KELORobile(kelo_ip)          # connects directly to the server (peer mode, port 7447)

# Drive forward at 0.2 m/s. The setpoint reverts to zero after `timeout` seconds (default 1.0),
# so to keep moving you call this repeatedly.
client.set_platform_velocity_target(0.2, 0.0, 0.0, timeout=1.0)

# Read back the estimated pose [x, y, a] and velocity [vx, vy, va].
print("pose:", client.get_odometry())
print("velocity:", client.get_velocity())

client.close()
```

When `KELORobile` is constructed it opens a Zenoh session, starts streaming the velocity setpoint in a
background thread, and performs a handshake with the server (which verifies the version match). If the
handshake fails or no reply arrives, construction raises a `KELORobileError` — check that the server is
running and reachable.

## What's next

- [Client usage](client_usage.md) — the full `KELORobile` API: driving, alignment, compliant mode,
  reading state, and lifecycle.
- [Server usage](server_usage.md) — configuring and running the server, the YAML format, and peer vs.
  router connectivity.
