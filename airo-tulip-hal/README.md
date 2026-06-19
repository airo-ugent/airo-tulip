# AIRO Tulip HAL

The `airo-tulip-hal` package is the **h**ardware **a**bstraction **l**ayer for the KELO Robile platform.
It contains the EtherCAT driver, platform monitor, controllers, and the `TulipServer` that accepts
commands over the network. **This package runs on the KELO CPU brick.**

It is the counterpart of the lightweight [`airo-tulip`](../airo-tulip/README.md) package, which contains
the client (`KELORobile`) and the shared API contract. A laptop or workstation that only needs to *control*
the robot should install `airo-tulip` (which does not depend on `pysoem` or any hardware libraries);
the KELO CPU brick installs `airo-tulip-hal`.

```
laptop / workstation         KELO CPU brick
┌──────────────────┐  TCP    ┌────────────────────────┐
│ airo-tulip       │ ◀─────▶ │ airo-tulip-hal         │
│  KELORobile      │  0MQ    │  TulipServer           │
│                  │         │  hardware / EtherCAT   │
└──────────────────┘         └────────────────────────┘
```

## Installation

```shell
pip install airo-tulip-hal
```

This installs `airo-tulip` (the shared contract) as a dependency, along with `pysoem` for EtherCAT
communication. Requires Python 3.9+.

## Running the server on the KELO

The server connects (over Zenoh) to a Zenoh **router** (`zenohd`), which by default runs on the KELO CPU
brick. `install.sh` sets all of this up: it installs the router, seeds a `robot.yaml` config, and runs the
server as a systemd service on boot.

**Prerequisite:** a Zenoh router (`zenohd`) must be running. Install it from the
[zenoh releases](https://github.com/eclipse-zenoh/zenoh/releases) and start it on the KELO CPU brick
(the install script does this for you).

The server is launched by the `airo-tulip-server` console script, which reads a YAML config describing
your platform (the EtherCAT device and the drive layout — provided by KELO with your platform):

```shell
airo-tulip-server --config robot.yaml
```

A documented example config is in [`../deploy/robot.example.yaml`](../deploy/robot.example.yaml):

```yaml
ethercat_device: eno1
wheels:
  - { ethercat_number: 3, x: 0.233,  y: 0.1165,  a: 1.57 }
  - { ethercat_number: 5, x: 0.233,  y: -0.1165, a: 1.57 }
  - { ethercat_number: 7, x: -0.233, y: -0.1165, a: -1.57 }
  - { ethercat_number: 9, x: -0.233, y: 0.1165,  a: 1.57 }
# Optional: robot_id, router_endpoint, loop_frequency, watchdog_timeout
```

If you prefer to embed the server in your own Python program, you can still construct
`airo_tulip_hal.server.TulipServer` with a `RobotConfiguration` directly.

Connect to it from a client as documented in the [`airo-tulip`](../airo-tulip/README.md) README.

## Structure

For more information on how the hardware abstraction layer is structured, and why, refer to
[`../airo-tulip/docs/how_it_works.md`](../airo-tulip/docs/how_it_works.md).
