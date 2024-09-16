# AIRO Tulip

The `airo-tulip` package is a Python port of the KELO Tulip software with some additional functionality.
You can use it to control the KELO Robile drives of a mobile platform and read out relevant sensor data from it.
The codebase is also structured a bit differently than the original C++ implementation provided by the manufacturer.

In this README, we'll go over the structure of the `airo-tulip` package and discuss some design choice that were made during the implementation.

This folder also contains additional documentation files:

- `rerun.md` on how to use Rerun running on the remote KELO CPU brick
- `virtual_display.md` on how to enable a virtual display for use in a VNC connection without needing to connect a display to the KELO CPU brick

## Installation

To install this package, clone the repository with `git` and use `pip` to install the `airo-tulip/` package.
Note that the `main` branch is the active development branch: you may want to check out a certain commit associated with
a version tag. The package requires at least Python 3.10.

For example, using [pyenv](https://github.com/pyenv) to set the local Python version to 3.10:

```shell
git clone https://github.com/airo-ugent/airo_kelo
cd airo_kelo
pyenv install 3.10 && pyenv local 3.10
python3 -m venv env
source env/bin/activate
pip install -e airo-tulip/
```

## Connecting to a UR cobot mounted on the KELO

If you want to connect to a UR cobot mounted on the KELO, you need to set up:

- The UR machine
- An SSH tunnel to the UR machine

### Setting up the UR

The following instructions were copied from [here](https://github.com/airo-ugent/airo-mono/blob/main/airo-robots/airo_robots/manipulators/hardware/universal_robots_setup.md).

Establish an Ethernet connection between the control box and the external computer:
* Connect a UTP cable from the control box to the external computer.
* Create a new network profile on the external computer in `Settings > Network > Wired > +`. Give it any name e.g. `UR` and in the IPv4 tab select `Shared to other computers`.
* On the control box, go to `Settings > System > Network` and select Static Address and set:
    * IP address: `10.42.0.162`
    * Subnet mask: `255.255.255.0`
    * Gateway: `10.42.0.1`
    * Preferred DNS server: `10.42.0.1`

On macOS, this corresponds to creating a network with IPv4 configured manually at 10.42.0.1 (subnet mask 255.255.0.0) and configure IPv4 automatically.

If you're lucky, the control box will already say "Network is connected".
If pinging the control box from the external computer works, you're done and can read the next section to Enable remote control mode:

```bash
ping 10.42.0.162
```

If not, you can try to manually bringing up the network profile you created:

```bash
nmcli connection up UR
```

If pinging still doesn't work, try restarting the robot control box.
If still not successful, try swapping Ethernet cables, ports or computers.

Now, make sure the robot is in remote control.

### Setting up an SSH tunnel

The UR robot listens on ports 29999, 30001, 30002, 30003 and 30004. To access them on, e.g., your laptop through the KELO NUC,
you need to set up an SSH tunnel. Assuming that the KELO's IP address is 10.10.129.20:

```commandline
ssh -N -L localhost:29999:10.42.0.162:29999 -L localhost:30001:10.42.0.162:30001 -L localhost:30002:10.42.0.162:30002 -L localhost:30003:10.42.0.162:30003 -L localhost:30004:10.42.0.162:30004 kelo@10.10.129.20
```

Now, you can access the UR robot via `localhost` on your laptop:

```python
from airo_robots.manipulators.hardware.ur_rtde import URrtde

ur = ur_rtde.URrtde("localhost", ur_rtde.URrtde.UR3E_CONFIG)
print(ur.get_tcp_pose())
```

### Robotiq 2F85

The Robotiq 2F85 gripper communicates on port 63352, so you should also create an SSH tunnel for this.


```commandline
ssh -N -L localhost:63352:10.42.0.162:63352 kelo@10.10.129.20
```

The two tunnels can be set up in one single command:

```commandline
ssh -N -L localhost:29999:10.42.0.162:29999 -L localhost:30001:10.42.0.162:30001 -L localhost:30002:10.42.0.162:30002 -L localhost:30003:10.42.0.162:30003 -L localhost:30004:10.42.0.162:30004 -L localhost:63352:10.42.0.162:63352 kelo@10.10.129.20
```

### Turning on the robot arm remotely

See `../utils/start_ur.py` and `../utils/stop_ur.py` to start the robot arm remotely, without needing to connect
peripherals and/or a monitor.

### Automatically starting the robot on boot

You can set up the KELO to start the robot arm automatically on boot, by editing the root user's crontab file.

```commandline
sudo crontab -e
```

Enter the following line(s) at the bottom:

```
@reboot /home/kelo/start_server.sh
@reboot /home/kelo/start_ur.sh
```

Copy the `airo-tulip/utils/start_server.sh` and `airo-tulip/utils/start_ur.sh` scripts to the `/home/kelo` directory
and reboot. The server and UR should start automatically and the UR should release its brakes.

## Connecting to other devices mounted on the KELO

You can mount other devices on the KELO, and patch them to the KELO via Ethernet. Follow the instructions above to set up the KELO as a router, and assign a static IP address to the device you have mounted on the KELO.

The device will be able to access the KELO at IP address `10.42.0.1` and will be accessible through the KELO via SSH tunnels, as explained above for the UR arm.

## Structure

The `airo-tulip` package consists of the following main Python classes and files:
- `RobilePlatform`: the main class for representing a complete KELO Robile system. It initializes the various drives of the robot via EtherCAT and handles the higher-level operations of the system.
- `PlatformDriver`: driver for transmitting specific setpoints for the wheel to all drives. Controls the state of the drives and startup procedure.
- `PlatformMonitor`: module that reads out the sensor data from EtherCAT messages and caches them for later retrieval.
- `VelocityPlatformController`: controller that calculates the setpoints for each wheel in velocity mode. One can set a target velocity in 2D for the complete platform and this controller will convert that to angular velocities for each of the drives.

Later on, we'll add more types of controllers to also support e.g., torque control and compliant control. These new controller classes will be added to the `airo_tulip.controllers` module.

The `RobilePlatform` class instantiates a `PlatformDriver` and a `PlatformMonitor` in its constructor. These objects are available in the `driver` and `monitor` properties of the `RobilePlatform` class respectively. The `VelocityPlatformController` is instantiated by the `PlatformDriver` but not available through properties in the `PlatformDriver`. One can set a target velocity using a wrapper method in the `RobilePlatform` class.

### Communication with `airo-tulip`

The `airo-tulip` package has a subpackage called `server`. When working with the KELO Robile platform, you want to run the `TulipServer` on boot, typically,
so that commands can be sent over the network. The `TulipServer` takes a desired IP address and port, which can be used to connect to it via a client.
A client example can be found in `test_client.py`.

The server is implemented via [0MQ](https://pyzmq.readthedocs.io/en/latest/), so it does not work over raw TCP sockets, but rather uses a higher level of abstraction.
The server accepts messages, defined in `airo_tulip.server.messages`, which can be sent using `zmq.Socket.send_pyobj`: these messages are pickled,
resp. unpickled, and contain the relevant information to drive the KELO Robile system via the `RobilePlatform` interface.

When using `airo-tulip`, we recommend building an abstraction layer over your client, so that users only need to call methods such as
`robile.set_platform_velocity_target()` and do not need to work with message objects directly.

## Velocity limits

The drives of the KELO Robile are quite strong, so care should be taken when controlling them.
The `airo-tulip` package incorporates various safety checks to limit the speed and torque of each of the wheels.

For example, one cannot set a platform target velocity higher than 0.5 m/s linear or pi/8 rad/s angular in the wrapper method of the `RobilePlatform` class.
The acceleration and deceleration of each drive is limited to 0.5 m/s^2 linear and 0.8 m/s^2 angular by attributes of the `PlatformLimits` dataclass that is used in the `VelocityPlatformController`.
Additionally, the value for each wheel setpoint is once more limited by the `_wheel_set_point_max` attribute in the `PlatformDriver` class.
And the maximum current that the motors of each drive will supply is limited to 20 amps during acceleration and 1 amp during braking, as specified in each EtherCAT message that is transmitted.

Do not overrule or change these limits unless you really need them and know what you're doing!

## EtherCAT

The KELO Robile makes use of an EtherCAT bus for communication between the various modular bricks.
As such, the integrated compute brick on which the `airo-tulip` package runs, needs to send and receive EtherCAT messages to and from this shared bus.
For this, we make use of the `PySOEM` library.

An EtherCAT bus works by daisy-chaining nodes on the bus.
To communicate over the bus, an EtherCAT telegram is constructed on the master node (the compute brick in the case of a KELO Robile) and transmitted on the bus to the first slave device.
The first slave device checks if there is any data in the telegram for itself, reads it and optionally write its own data into the telegram.
It also increases the *working counter* field in the telegram if it read or wrote from or to the telegram.
Finally, the slave device sends the telegram to the next device in the chain.
At the end, the telegram is reflected and sent back to the master.
A neat animation visualizing the workings of an EtherCAT bus can be found [here](https://en.wikipedia.org/wiki/File:EthercatOperatingPrinciple.webm).

The `RobilePlatform` class creates a `pysoem.Master` object that controls the EtherCAT bus.
After the initialisation process described in `RobilePlatform.init_ethercat()`, each of the drives connected to the EtherCAT bus is represented as a slave device under this master object.
One can read from each slave device using the `output` buffer and write to it using `input` buffer.
The contents of these buffers is represented by the `TxPDO1` and `RxPDO1` structs specified in `ethercat.py`.
The naming of these buffers might be a bit counterintuitive as you need a `TxPDO1` struct and the `output` buffer to read from a slave device, so be cautious!
We've provided the `_get_process_data()` and `_set_process_data()` functions to easily read and write from the buffers using the `TxPDO1` and `RxPDO1` structs.

Note that you'll find that there are 9 slaves in total: 2 times 4 drives and 1 compute unit.
Only one of the two slaves for each drive is addressable via input and output buffers, the other doesn't have any.

Drives continuously need to receive EtherCAT telegrams in order for them to stay enabled.
If too much time passes since the last time they received data, the drives will automatically go into a safe state and stop supplying current to the motors.
Therefor, the `RobilePlatform.step()` function needs to be called inside the main application update loop, preferably at a frequency of 20 Hz.
This limitation poses special requirements on the implementation of the driver code, as it is run in a separate thread to ensure that it is called without interruption.


