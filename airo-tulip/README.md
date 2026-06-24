# AIRO Tulip

The `airo-tulip` package is a Python port of the KELO Tulip software with some additional functionality.
You can use it to control the KELO Robile drives of a mobile platform and read out relevant sensor data from it.
The structure of the code base is different from that of the original C++ implementation provided by the manufacturer.

In this README, we over the structure of the `airo-tulip` package and discuss some design choices that were made during the implementation.

The `docs` folder contains additional documentation files (in no particular order):

- `kelo_setup.md` on how to set up the KELO hardware and software, a prerequisite to using `airo-tulip`
- `external_devices.md` on how to connect to other devices mounted on the KELO, with the KELO acting as the router
- `how_it_works.md` on how the code base is structured and why

Even though you don't need to understand or even read *all* of these to use `airo-tulip`,
we do recommend it to get a holistic overview of how the platform works and
why `airo-tulip` is implemented the way it is.

## How to use this package

The project is split into two packages:

- **`airo-tulip`** (this package) contains the client (`KELORobile`) and the shared API contract
  (`airo_tulip.api.messages`, `airo_tulip.api.types`). Install it on any device that controls the robot
  over the network (laptop, workstation, NUC). It does **not** depend on `pysoem` or any hardware library.
- **`airo-tulip-hal`** contains the hardware abstraction layer (EtherCAT driver, monitor, controllers) and
  the `TulipServer`. It runs on the KELO CPU brick. See [`../airo-tulip-hal/README.md`](../airo-tulip-hal/README.md).

The client communicates with the server over Zenoh. This README documents the client side;
for running the server, see the `airo-tulip-hal` README.

**Note:** when interfacing with the server from a client on a remote machine, make sure that the `airo-tulip` versions
match on client and server, or else you may observe unexpected behaviour or crashes (this is checked during the handshake).

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

### Running the server on the KELO

The server (`TulipServer`) lives in the separate `airo-tulip-hal` package and runs on the KELO CPU brick.
See [`../airo-tulip-hal/README.md`](../airo-tulip-hal/README.md) for how to configure and start it.

### Connecting to the `airo-tulip` server

Once the server is running on the KELO, connect with an `api.client.KELORobile` instance. By default
`KELORobile` connects directly to the server (Zenoh peer mode) at `tcp/<kelo_ip>:7447`:

```python
from airo_tulip.api.client import KELORobile

kelo_ip = "10.10.129.21"
client = KELORobile(kelo_ip)
```

You can then send commands to the KELO platform by calling the methods on the `client` object, e.g.,

```python
client.set_platform_velocity_target(0.5, 0.0, 0.0, timeout=1.0)
```

to drive at 0.5 m/s along the platform's +X axis. The velocity setpoint is streamed to the server and
automatically reverts to zero after `timeout` seconds; to keep driving, call it again (or repeatedly).
Read back the platform's state with `client.get_odometry()`, `client.get_velocity()`,
`client.are_drives_aligned()`, and `client.get_status()` (driver mode, alignment, per-drive health).

### Mounted devices

You can mount additional devices on the KELO (sensors, a more powerful compute unit, etc.) and reach them
over the network through the brick. Refer to [`docs/external_devices.md`](docs/external_devices.md) for how
to set up and access external devices.

### Odometry
The default odometry is based on the drive encoders and is not always robust. We recommend using additional sensors such as a compass or flow sensor to improve the odometry.

## Structure

For more information on how this code base is structured, and why, please refer to [`docs/how_it_works.md`](docs/how_it_works.md).
