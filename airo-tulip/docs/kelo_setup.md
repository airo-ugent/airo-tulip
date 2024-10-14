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

### At IDLab-AIRO

There is a known issue with the platform we use at IDLab-AIRO where the `KELO` connection profile is not selected automatically on boot.
You need to select it manually **and** through the GUI, for which you need to create this virtual display.

Any attempts to automatically select this connection profile with the connection manager appear to fail, and using the
GUI is the recommended approach until we find the cause of this issue.

## Connecting external sensors and LEDs

You may want to connect external sensors and/or LEDs to your platform. We've done this at IDLab-AIRO!
We mount a Teensy microcontroller on the robot, which can address the LEDs and read out optical flow sensors.
As soon as the Teensy microcontroller is powered on, it can be instructed from the KELO NUC over a USB serial interface.

See the `peripherals` folder in the root directory of this repository for more information.
