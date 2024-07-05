import time

from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.structs import WheelConfig


def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()
    mobi = RobilePlatform(device, wheel_configs)
    mobi.init_ethercat()

    # Loop indefinitely
    while True:
        mobi.step()
        fancy_print_sensors(mobi.monitor)
        time.sleep(0.050)


def fancy_print_sensors(monitor):
    for i in range(4):
        print(f"accel {i} ", monitor.get_acceleration(i))
        print(f"temp {i} ", monitor.get_temperature(i))
    print()


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
