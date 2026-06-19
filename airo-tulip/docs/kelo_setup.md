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
