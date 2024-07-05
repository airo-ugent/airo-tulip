import math
import time

from airo_tulip.server.client import Client


def test():
    client = Client("localhost", 49789)

    client.set_platform_velocity_target(0.5, 0.0, 0.0)
    time.sleep(3)  # movement should timeout

    client.set_platform_velocity_target(0.0, 0.0, math.pi / 8, timeout=2.0)
    time.sleep(2)

    client.set_platform_velocity_target(0.2, 0.0, 0.0)
    time.sleep(1)

    client.set_platform_velocity_target(0.0, 0.2, 0.0)
    time.sleep(1)

    client.set_platform_velocity_target(-0.2, 0.0, 0.0)
    time.sleep(1)

    client.set_platform_velocity_target(0.0, -0.2, 0.0)
    time.sleep(1)

    client.set_platform_velocity_target(0.0, 0.0, -math.pi / 8, timeout=2.0)
    time.sleep(2)

    client.set_platform_velocity_target(-0.5, 0.0, 0.0)
    time.sleep(1)  # movement should timeout

    client.set_platform_velocity_target(0.0, 0.0, 0.0)
    time.sleep(0.5)

    client.stop_server()
    time.sleep(0.5)


if __name__ == "__main__":
    test()
