import time

from airo_tulip.platform_driver import PlatformDriverType
from airo_tulip.server.kelo_robile import KELORobile

def move_direction(mobi, x, y, a):
    mobi.set_driver_type(PlatformDriverType.VELOCITY)
    mobi.align_drives(x, y, a, timeout=2.0)
    time.sleep(2.0)

    mobi.set_driver_type(PlatformDriverType.COMPLIANT_WEAK)
    mobi.set_platform_velocity_target(x, y, a, timeout=5.0)


def test():
    mobi = KELORobile("localhost", 49789)

    move_direction(mobi, 0.5, 0.0, 0.0)
    move_direction(mobi, 0.0, 0.5, 0.0)
    move_direction(mobi, -0.5, 0.0, 0.0)
    move_direction(mobi, 0.0, -0.5, 0.0)

    mobi.stop_server()
    time.sleep(0.5)


if __name__ == "__main__":
    test()
