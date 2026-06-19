import math
import time

from airo_tulip.api.client import KELORobile
from airo_tulip.api.types import PlatformDriverType


def main():
    mobi = KELORobile("localhost")  # connects to a Zenoh router on localhost:7447

    mobi.set_driver_type(PlatformDriverType.COMPLIANT_WEAK)

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
    main()
