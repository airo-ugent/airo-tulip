import math
import time

from airo_tulip.api.client import KELORobile


def test():
    mobi = KELORobile("localhost", 49789)

    mobi.set_platform_velocity_target(0.2, 0.0, 0.0)
    time.sleep(3)  # movement should timeout

    mobi.set_platform_velocity_target(0.0, 0.0, math.pi / 8, timeout=2.0)
    time.sleep(2)

    mobi.set_platform_velocity_target(0.2, 0.0, 0.0)
    time.sleep(1)

    mobi.set_platform_velocity_target(0.0, 0.2, 0.0)
    time.sleep(1)

    mobi.set_platform_velocity_target(-0.2, 0.0, 0.0)
    time.sleep(1)

    mobi.set_platform_velocity_target(0.0, -0.2, 0.0)
    time.sleep(1)

    mobi.set_platform_velocity_target(0.0, 0.0, -math.pi / 8, timeout=2.0)
    time.sleep(3)

    mobi.set_platform_velocity_target(-0.2, 0.0, 0.0, timeout=3.0)
    time.sleep(3)  # movement should timeout

    mobi.set_platform_velocity_target(0.0, 0.0, 0.0)
    time.sleep(0.5)

    mobi.stop_server()
    time.sleep(0.5)


if __name__ == "__main__":
    test()
