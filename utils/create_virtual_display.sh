#!/usr/bin/env bash

# Create a virtual display that can be accessed via VNC

export DISPLAY=:1
Xvfb "$DISPLAY" -screen 0 1024x768x16 &
x11vnc -display "$DISPLAY" &
gnome-shell --replace
