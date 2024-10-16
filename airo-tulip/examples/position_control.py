import math
import time

from airo_tulip.api.client import KELORobile

from api.client import KELORobileError


def test():
    mobi = KELORobile("localhost", 49789)

    mobi.move_platform_to_pose(1.0, 0.0, 0.0, 10.0)

    try:
        mobi.set_platform_velocity_target(0.0, 0.0, 0.0, 1.0)
        print("Expected an exception, but didn't get it...")
    except KELORobileError:
        print("Expected an exception and got it!")  # We want an exception here.

    while not mobi.position_control_loop_reached_target():
        print("Not yet there...")
        time.sleep(1.0)

    mobi.move_platform_to_pose(0.0, 0.0, 0.0, 10.0)
    time.sleep(0.5)
    mobi.stop_position_control_loop()
    try:
        mobi.set_platform_velocity_target(0.2, 0.0, 0.0, 1.0)
        print("Didn't get an exception this time, which is good!")
    except KELORobileError:
        print("Got an exception, which is bad...")

    mobi.stop_server()
    time.sleep(0.5)


if __name__ == "__main__":
    test()
