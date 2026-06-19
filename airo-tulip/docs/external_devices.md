# Connecting to external devices

There is not much you can do with the KELO platform without external devices mounted on it.
We recommend using the KELO's CPU brick as a router, and connecting external devices over Ethernet to it.
All devices are then accessible from the KELO with a static IP address.

You must first set up the KELO's network for this. Please refer to [`kelo_setup.md`](./kelo_setup.md) before continuing.

## Connecting to a mounted device

You can mount devices on the KELO and patch them to the brick over Ethernet. Set the KELO up as a router
(see [`kelo_setup.md`](./kelo_setup.md)) and assign the mounted device a static IP address in the brick's
subnet. The brick is reachable at `10.42.0.1`, so a device might be configured as:

- IP address: `10.42.0.x`
- Subnet mask: `255.255.255.0`
- Gateway / DNS: `10.42.0.1`

If the network connection on the brick is not up, bring it up (and verify connectivity):

```bash
nmcli connection up KELO
ping 10.42.0.x
```

### Accessing a device's ports via an SSH tunnel

To reach a mounted device's ports from, e.g., your laptop through the KELO brick, set up an SSH tunnel.
Assuming the KELO's IP is `10.10.129.21`, the device is at `10.42.0.x`, and it listens on port `PORT`:

```commandline
ssh -N -L localhost:PORT:10.42.0.x:PORT kelo@10.10.129.21
```

Forward multiple ports by repeating `-L localhost:PORT:10.42.0.x:PORT` in a single command. The device is
then reachable on `localhost:PORT` on your laptop.

### Robot-mounted NUC: boot when powered

At AIRO, we mounted a more powerful NUC on the robot for deep learning inference workloads. To
automatically boot the NUC whenever the KELO is turned on, connect it to the NUC's battery for power.
Enter the NUC's BIOS and set the option to power on after power loss. The NUC should now boot as soon as
the KELO robot is turned on.

It is recommended to always cleanly shut down the NUC (and the KELO brick as well), but this setting will
also allow you to restore power to it after (accidentally or on purpose) shutting off the power to the NUC.
