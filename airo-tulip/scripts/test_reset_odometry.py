import math
import time

from airo_tulip.server.kelo_robile import KELORobile


def test():
    mobi = KELORobile("localhost", 49789)

    mobi.reset_odometry()
    print(mobi.get_odometry())

    mobi.set_platform_velocity_target(-0.2, 0.0, 0.0)
    time.sleep(1.0)

    mobi.set_platform_velocity_target(0.0, 0.0, 0.0, timeout=1.0)

    print(mobi.get_odometry())
    mobi.reset_odometry()
    print(mobi.get_odometry())

    mobi.set_platform_velocity_target(0.2, 0.0, 0.0)
    time.sleep(1.0)

    mobi.set_platform_velocity_target(0.0, 0.0, 0.0, timeout=1.0)

    print(mobi.get_odometry())
    mobi.reset_odometry()
    print(mobi.get_odometry())


if __name__ == "__main__":
    test()
