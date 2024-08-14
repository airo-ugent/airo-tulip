# Virtual display

This document explains how you can debug visually (with matplotlib, open3d, rerun...) without connecting a display to
the KELO robot over HDMI.

First, create a virtual X frame buffer:

```bash
export DISPLAY=:1
Xvfb "$DISPLAY" -screen 0 1024x768x16 &
```

Then start a VNC server on this display

```bash
x11vnc -display "$DISPLAY" &
```

Finally, start a gnome shell to enable the gnome desktop environment:

```bash
gnome-shell --replace
```

Now you can connect with a VNC server (Ubuntu comes with Remmina pre-installed) to `10.10.129.20:5900`,
with `10.10.129.20` the KELO's IP address.
