"""Start the UR robot arm remotely, without needing to connect a monitor and peripherals to the control box."""
import argparse
import socket
import sys

from utils.start_ur import Dashboard

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, help="IP address of the UR control box", default="localhost")

    args = parser.parse_args()

    print("Setting up connection...")
    dash = Dashboard(args.ip)
    if dash.connect():
        print("Connected.")
    else:
        print("Failed to connect.")
        exit(1)
    # Check to see if robot is in remote mode.
    remote_check = dash.send_and_receive('is in remote control')
    if 'false' in remote_check:
        print("Robot is in local mode. Some commands may not function.\nYou will need to reboot the robot or manually enabled remote control.")
        exit(1)
    else:
        print("Robot is in remote mode. Will continue")

    print("Engaging brakes.")
    dash.send_and_receive("brake engage")

    print("Powering off.")
    dash.send_and_receive("power off")

    dash.close()
