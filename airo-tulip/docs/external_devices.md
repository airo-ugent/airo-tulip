# Connecting to external devices

There is not much you can do with the KELO platform without external devices mounted on it.
We recommend using the KELO's CPU brick as a router, and connecting external devices over Ethernet to it.
All devices are then accessible from the KELO with a static IP address.

You must first set up the KELO's network for this. Please refer to [`kelo_setup.md`](./kelo_setup.md) before continuing.

## Connecting to a UR cobot mounted on the KELO

If you want to connect to a UR cobot mounted on the KELO, you need to set up:

- The UR machine
- An SSH tunnel to the UR machine

### Setting up the UR

Make sure you followed the instructions in [`kelo_setup.md`](./kelo_setup.md) to set up the network on the KELO CPU brick.

* On the control box, go to `Settings > System > Network` and select Static Address and set:
    * IP address: `10.42.0.162`
    * Subnet mask: `255.255.255.0`
    * Gateway: `10.42.0.1`
    * Preferred DNS server: `10.42.0.1`

If you're lucky, the control box will already say "Network is connected".
You should be able to ping the control box.

```bash
ping 10.42.0.162
```

If not, make sure that the correct network connection is up **on the KELO CPU brick**:

```bash
nmcli connection up KELO
```

If pinging still doesn't work, try restarting the robot control box.

### Setting up an SSH tunnel

The UR robot listens on ports 29999, 30001, 30002, 30003 and 30004. To access them on, e.g., your laptop through the KELO NUC,
you need to set up an SSH tunnel. Assuming that the KELO's IP address is 10.10.129.21:

```commandline
ssh -N -L localhost:29999:10.42.0.162:29999 -L localhost:30001:10.42.0.162:30001 -L localhost:30002:10.42.0.162:30002 -L localhost:30003:10.42.0.162:30003 -L localhost:30004:10.42.0.162:30004 kelo@10.10.129.21
```

Now, you can access the UR robot via `localhost` on your laptop:

```python
from airo_robots.manipulators.hardware.ur_rtde import URrtde

ur = URrtde("localhost", URrtde.UR3E_CONFIG)
print(ur.get_tcp_pose())
```

### Robotiq 2F85

The Robotiq 2F85 gripper communicates on port 63352, so you should also create an SSH tunnel for this.


```commandline
ssh -N -L localhost:63352:10.42.0.162:63352 kelo@10.10.129.21
```

The two tunnels can be set up in one single command:

```commandline
ssh -N -L localhost:29999:10.42.0.162:29999 -L localhost:30001:10.42.0.162:30001 -L localhost:30002:10.42.0.162:30002 -L localhost:30003:10.42.0.162:30003 -L localhost:30004:10.42.0.162:30004 -L localhost:63352:10.42.0.162:63352 kelo@10.10.129.21
```

### Turning on the robot arm remotely

See `../utils/start_ur.py` and `../utils/stop_ur.py` to start the robot arm remotely, without needing to connect
keyboard and mouse and a monitor.

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

### Robot-mounted NUC: boot when powered

At AIRO, we mounted a more powerful NUC on the robot for deep learning inference workloads. To automatically boot the NUC whenever the KELO is turned on, connect it to the NUC's battery for power. Enter the NUC's BIOS and set the option to power on after power loss. The NUC should now boot as soon as the KELO robot is turned on.

It is recommended to always cleanly shut down the NUC (and the KELO NUC as well), but this setting will also allow you to restore power to it after (accidentally or on purpose) shutting off the power to the NUC.

### Other peripherals

At AIRO, we use other peripherals, such as optical flow sensors but also LED strips, controlled via a [Teensy](https://www.pjrc.com/teensy/) over USB. See [this folder](https://github.com/airo-ugent/airo-tulip/tree/peripherals/peripherals) for more information.
