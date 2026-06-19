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
│  (no pysoem)     │         │  hardware / EtherCAT   │
└──────────────────┘         └────────────────────────┘
```

## Installation

```shell
pip install airo-tulip-hal
```

This installs `airo-tulip` (the shared contract) as a dependency, along with `pysoem` for EtherCAT
communication. Requires Python 3.9+.

## Running the server on the KELO

`airo_tulip_hal.server` provides `TulipServer`, which initialises the KELO platform and accepts an
incoming connection from an `airo_tulip.api.client.KELORobile`. To accept connections from any device on
the network, listen on `0.0.0.0`. The `RobotConfiguration` is specific to how the KELO bricks are mounted
(provided by KELO robotics with your platform), as is the EtherCAT device name.

```python
from airo_tulip_hal.server import TulipServer, RobotConfiguration
from airo_tulip_hal.hardware.structs import WheelConfig


def create_wheel_configs():
    wheel_configs = []
    wheel_configs.append(WheelConfig(ethercat_number=3, x=0.233, y=0.1165, a=1.57))
    wheel_configs.append(WheelConfig(ethercat_number=5, x=0.233, y=-0.1165, a=1.57))
    wheel_configs.append(WheelConfig(ethercat_number=7, x=-0.233, y=-0.1165, a=-1.57))
    wheel_configs.append(WheelConfig(ethercat_number=9, x=-0.233, y=0.1165, a=1.57))
    return wheel_configs


# These values are specific to your platform!
device = "eno1"
server = TulipServer(RobotConfiguration(device, create_wheel_configs()), "0.0.0.0")
server.run()
```

Connect to it from a client as documented in the [`airo-tulip`](../airo-tulip/README.md) README.

## Structure

For more information on how the hardware abstraction layer is structured, and why, refer to
[`../airo-tulip/docs/how_it_works.md`](../airo-tulip/docs/how_it_works.md).
