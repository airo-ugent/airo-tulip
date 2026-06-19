# AIRO Tulip

This repository contains:

- The KELO robotics C++ implementation of the KELO Robile platform driver, called KELO Tulip (`./kelo_tulip`)
- A Python reimplementation with altered and additional functionality by IDLab-AIRO (UGent-imec) for integration in Python projects without a ROS dependency, split into a lightweight client/contract package (`./airo-tulip`) and a hardware abstraction layer that runs on the KELO CPU brick (`./airo-tulip-hal`)
- A folder `./utils` with utility scripts
- A script `./install.sh` which installs the necessary dependencies for the KELO Tulip and AIRO Tulip packages and puts several commands on the path

See the respective subdirectories for more information.

## Installation

You can run `./install.sh` to install the `airo-tulip` package and other commands to a KELO CPU brick running Ubuntu.
This script will install airo-tulip to directory from which it is executed.

There are some dependencies that need to be installed before you can install `airo-tulip` (normally these should be installed already):

```bash
sudo apt-get update -y
sudo apt-get install -y git gcc curl make
```

There is one other dependency which should be installed manually: `uv`.
As per the [official installation instructions](https://github.com/astral-sh/uv), you can install `uv` by running:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, the way to install `airo-tulip` is:

```bash
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
./install.sh
```

## Usage

After installation, the Zenoh router and the airo-tulip server start automatically when the KELO CPU brick boots.
You can then control the robot from any machine on the network with the `KELORobile` client (see
[`airo-tulip/README.md`](airo-tulip/README.md)) — drive it, read odometry/status, and enable/disable the
drives to save energy.
