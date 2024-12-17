# AIRO Tulip

This repository contains:

- The KELO robotics C++ implementation of the KELO Robile platform driver, called KELO Tulip (`./kelo_tulip`)
- A Python reimplementation with altered and additional functionality by IDLab-AIRO (UGent-imec) for integration in Python projects without a ROS dependency (`./airo-tulip`)
- A folder `./dashboard` which contains the implementation of a dashboard server that should run on the KELO CPU brick boot, that allows remote control of the KELO's peripherals such as the UR arm.
- A folder `./peripherals` with code that should run on the Teensy microcontroller that controls the peripherals
- A folder `./utils` with utility scripts
- A script `./install.sh` which installs the necessary dependencies for the KELO Tulip and AIRO Tulip packages and puts several commands on the path

See the respective subdirectories for more information.

## Installation

You can run `./install.sh` (as root) to install the `airo-tulip` package and other commands to a KELO CPU brick running Ubuntu.
This script should be run as the root user and will install airo-tulip to directory from which it is executed.

There are some dependencies that need to be installed before you can install `airo-tulip` (normally these should be installed already):

```bash
sudo apt-get update -y
sudo apt-get install -y git gcc curl make
```

There is one other dependency which should be installed manually: `pyenv`.
As per the [official installation instructions](https://github.com/pyenv/pyenv?tab=readme-ov-file#1-automatic-installer-recommended), you can install `pyenv` by running:

```bash
curl https://pyenv.run | bash
```

Then, the way to install `airo-tulip` is:

```bash
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
./install.sh
```

## Usage

After the installation, a dashboard server will automatically be started when the KELO CPU brick boots, listening on port 49790.
The server operates over TCP, and an example client can be found in `dashboard/airo_tulip_dashboard/example_client.py`.
