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

You can use `./install.sh` to install the `airo-tulip` package and other commands to a KELO CPU brick running Ubuntu.
This script should be run as the root user and will install airo-tulip to directory from which it is executed.
Hence, the way to install `airo-tulip` is:

```commandline
git clone https://github.com/airo-ugent/airo-tulip
cd airo-tulip
./install.sh
```
