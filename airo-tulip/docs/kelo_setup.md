# KELO set-up

When you first set up your mobile platform, you need to perform some installation steps to get up and running with
`airo-tulip`. It should come pre-installed with Ubuntu, which is already a great first step towards getting set up.

## Testing your platform with the pre-installed software

We recommend trying out the software that comes pre-installed on the NUC to verify that your hardware is still
working correctly after being shipped to you. You can connect a gamepad to the KELO CPU brick and use the
`kelo-tulip` software to teleoperate the platform.

## Using the KELO as the router of your platform

To use the KELO as the router of your platform and access mounted devices (see [`external_devices.md`](./external_devices.md))
over Ethernet, follow these instructions.

* Create a new network profile on the CPU brick in `Settings > Network > Wired > +`. Give it any name e.g. `KELO` and in the IPv4 tab select `Shared to other computers`.
* Bring up this network connection: `nmcli connection up KELO` (or use the GUI).
* On external devices that you wish to connect, give them a static address.

### Known issue

There is a known issue with the platform we use at IDLab-AIRO where the `KELO` connection profile is not selected automatically on boot.
Please read the following section about the virtual display to understand how to work around this issue.

## Avoiding running cables to a mobile robot

Of course, you want to avoid connecting cables to a mobile robot. If you need to debug something on the KELO CPU brick,
you will want to be able to access it remotely over Wi-Fi. We recommend setting up a virtual display (VNC server)
and connecting to it.

Please see the instructions in [`virtual_display.md`](./virtual_display.md) on how to do this.

Alternatively, if you wish to avoid running over VNC, you can also connect over ssh with X forwarding:

```shell
ssh -XC kelo
```

and then run

```shell
sudo -sE gnome-control-center
```

on the KELO.
