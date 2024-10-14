# AIRO Tulip

The `airo-tulip` package is a Python port of the KELO Tulip software with some additional functionality.
You can use it to control the KELO Robile drives of a mobile platform and read out relevant sensor data from it.
The structure of the code base is different from that of the original C++ implementation provided by the manufacturer.

In this README, we over the structure of the `airo-tulip` package and discuss some design choices that were made during the implementation.

The `docs` folder contains additional documentation files (in no particular order):

- `kelo_setup.md` on how to set up the KELO hardware and software, a prerequisite to using `airo-tulip`
- `rerun.md` on how to use Rerun running on the remote KELO CPU brick
- `virtual_display.md` on how to enable a virtual display for use in a VNC connection without needing to connect a display to the KELO CPU brick
- `external_devices.md` on how to connect to other devices mounted on the KELO, with the KELO acting as the router
- `how_it_works.md` on how the code base is structured and why

Even though you don't need to understand or even read *all* of these to use `airo-tulip`,
we do recommend it to get a holistic overview of how the platform works and
why `airo-tulip` is implemented the way it is.

## How to use this package

There are two layers to the `airo-tulip` package: the `hardware` module that interfaces with the KELO and other attached hardware,
and the `api` module that allows (optionally remote) users of the library to interface with this `hardware` over a TCP connection.
The code in the `hardware` module is supposed to be run on the KELO itself, while the code in the `api` module (more specifically in `api.client`)
can be run from any device that can access the KELO over Ethernet or Wi-Fi. While it possible to use `airo-tulip` without
`api`, by using `hardware.platform_driver` directly, this is not recommended, and we only document the usage through the `api` module.

**Note:** when interfacing with the server from a client on a remote machine, make sure that the `airo-tulip` versions
match on client and server, or else you may observe unexpected behaviour or crashes.

Using this package implies some hardware and software set-up on the KELO mobile platform itself, which is documented
in [`docs/kelo_setup.md`](docs/kelo_setup.md). If you simply use this library for robotics experiments, this set-up
will most likely have been performed for you. Still, please read that file thoroughly before continuing.
If you are the first to set up your custom KELO mobile platform, it is also recommended to read that file to get
up and running quickly.

### Installation

#### From PyPI

This package is available [on PyPI](https://pypi.org/project/airo-tulip/) and can be installed with one command:

```shell
pip install airo-tulip
```

Note that the package requires at least Python 3.9.

For example, using [pyenv](https://github.com/pyenv) to set the local Python version to 3.9:

```shell
pyenv install 3.9 && pyenv local 3.9
python3 -m venv env
source env/bin/activate
pip install airo-tulip
```

Or, using conda:

```shell
conda create -n airo-tulip-env python=3.9
conda activate airo-tulip-env
pip install airo-tulip
```

#### From GitHub

If you wish to install a development version, clone the repository with `git` and use `pip` to install the `airo-tulip/` package
in editable mode.
Note that the `main` branch is the active development branch: you may want to check out a certain commit associated with
a version tag.

Using pyenv:

```shell
git clone https://github.com/airo-ugent/airo_kelo
cd airo_kelo
pyenv install 3.9 && pyenv local 3.9
python3 -m venv env
source env/bin/activate
pip install -e airo-tulip/
```

Or using conda:

```shell
git clone https://github.com/airo-ugent/airo_kelo
cd airo_kelo
conda create -n airo-tulip-env python=3.9
conda activate airo-tulip-env
pip install -e airo-tulip/
```

### Running `airo-tulip` on the KELO

`airo_tulip.api.server` provides a class `TulipServer` which initializes the KELO platform and accepts an incoming
connection from a `airo_tulip.api.client.KELORobile`. To accept incoming connections from any device on the network,
listen on the IPv4 address `0.0.0.0`. The `RobotConfiguration` that must be supplied, is based on how the KELO bricks
are mounted. This information is received from KELO robotics together with your platform and is specific to your use case.
The EtherCAT device is also specific to your platform set-up.

To run the server, start it from a Python script:

```python
from airo_tulip.api.server import TulipServer, RobotConfiguration
from airo_tulip.hardware.structs import WheelConfig

def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig(
        ethercat_number=3,
        x=0.233,
        y=0.1165,
        a=1.57
    )
    wheel_configs.append(wc0)

    wc1 = WheelConfig(
        ethercat_number=5,
        x=0.233,
        y=-0.1165,
        a=1.57
    )
    wheel_configs.append(wc1)

    wc2 = WheelConfig(
        ethercat_number=7,
        x=-0.233,
        y=-0.1165,
        a=-1.57
    )
    wheel_configs.append(wc2)

    wc3 = WheelConfig(
        ethercat_number=9,
        x=-0.233,
        y=0.1165,
        a=1.57
    )
    wheel_configs.append(wc3)

    return wheel_configs

# These values are specific to your platform!
device = "eno1"
wheel_configs = create_wheel_configs()

server = TulipServer(RobotConfiguration(device, wheel_configs), "0.0.0.0")
server.run()
```

### Connecting to the `airo-tulip` server

Once you have started the server on the KELO, you can connect to it with an `api.client.KELORobile` instance:

```python
from airo_tulip.api.client import KELORobile

kelo_ip = "10.10.129.21"
client = KELORobile(kelo_ip)
```

You can then send commands to the KELO platform by calling the methods on the `client` object, e.g.,

```python
client.set_platform_velocity_target(0.5, 0.0, 0.0, timeout=1.0)
```

to drive approximately 0.5 meters, at 0.5 meters per second, along the platform's +X axis.

### Mounted devices

Without mounting external devices on the KELO, you can pretty much only drive around (which is cool, but not very useful).
Refer to [`docs/external_devices.md`](docs/external_devices.md) for information on how to set up and access external devices
such as a UR cobot with a Robotiq gripper.

## Structure

For more information on how this code base is structured, and why, please refer to [`docs/how_it_works.md`](docs/how_it_works.md).
