# AIRO Tulip Dashboard

This folder contains the implementation of a dashboard server that should run on the KELO CPU brick boot, that allows
remote control of the KELO's peripherals such as the UR arm.
This dashboard server is implemented specifically for the set-up at IDLab-AIRO, and is not meant to be a general-purpose
dashboard server.
Nevertheless, it can serve as an example for how to implement a dashboard server for your own custom KELO set-up.

At AIRO, we install the dashboard server by `pip install`ing it with the `install.sh` script in the root of
the [repository](https://github.com/airo-ugent/airo-tulip).