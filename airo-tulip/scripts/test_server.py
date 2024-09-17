import asyncio

from airo_tulip.server.server import TulipServer, RobotConfiguration
from airo_tulip.structs import WheelConfig


def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()

    server = TulipServer(RobotConfiguration(device, wheel_configs), "0.0.0.0")
    server.run()


def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig(
        ethercat_number=3,
        x=0.233,
        y=0.1165,
        a=1.57
    )
    wheel_configs.append(wc0)

    wc1 = WheelConfig(
        ethercat_number=5,
        x=0.233,
        y=-0.1165,
        a=1.57
    )
    wheel_configs.append(wc1)

    wc2 = WheelConfig(
        ethercat_number=7,
        x=-0.233,
        y=-0.1165,
        a=-1.57
    )
    wheel_configs.append(wc2)

    wc3 = WheelConfig(
        ethercat_number=9,
        x=-0.233,
        y=0.1165,
        a=1.57
    )
    wheel_configs.append(wc3)

    return wheel_configs


if __name__ == "__main__":
    test()
