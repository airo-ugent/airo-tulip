import time

from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.platform_driver import PlatformDriverType
from airo_tulip.structs import WheelConfig


def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()
    mobi = RobilePlatform(device, wheel_configs, PlatformDriverType.VELOCITY)
    mobi.init_ethercat()

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 1:
        mobi.step()
        time.sleep(0.050)

    # Set target velocity
    mobi.driver.set_platform_velocity_target(0.0, 0.0, 3.14/8, timeout=4)

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 4:
        mobi.step()
        time.sleep(0.050)

    # Set zero target velocity
    mobi.driver.set_platform_velocity_target(0.0, 0.0, 0.0, timeout=1)

    # Loop indefinitely
    while True:
        mobi.step()
        time.sleep(0.050)


def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig(ethercat_number=3, x=0.233, y=0.1165, a=1.57)
    wheel_configs.append(wc0)

    wc1 = WheelConfig(ethercat_number=5, x=0.233, y=-0.1165, a=1.57)
    wheel_configs.append(wc1)

    wc2 = WheelConfig(ethercat_number=7, x=-0.233, y=-0.1165, a=-1.57)
    wheel_configs.append(wc2)

    wc3 = WheelConfig(ethercat_number=9, x=-0.233, y=0.1165, a=1.57)
    wheel_configs.append(wc3)

    return wheel_configs


if __name__ == "__main__":
    test()
