import time

from airo_tulip.platform_driver import PlatformDriverType
from airo_tulip.server.kelo_robile import KELORobile


def test():
    mobi = KELORobile("localhost", 49789)

    mobi.align_drives(0.1, 0.0, 0.0, timeout=2.0)
    time.sleep(2.0)

    mobi.set_driver_type(PlatformDriverType.COMPLIANT_WEAK)
    mobi.set_platform_velocity_target(0.2, 0.0, 0.0, timeout=10.0)
    time.sleep(2.0)
    exit(1)

    mobi.set_platform_velocity_target(0.5, 0.0, 0.0, timeout=3.0)
    time.sleep(3.0)

    mobi.set_platform_velocity_target(0.0, 0.0, 0.0)
    time.sleep(3.0)

    mobi.stop_server()
    time.sleep(0.5)


if __name__ == "__main__":
    test()
