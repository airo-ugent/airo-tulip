import time
import matplotlib.pyplot as plt

from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.structs import WheelConfig
from airo_tulip.platform_driver import PlatformDriverType, PlatformDriverState

def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()
    mobi = RobilePlatform(device, wheel_configs, PlatformDriverType.COMPLIANT)
    mobi.driver._wheel_enabled = [False] * len(wheel_configs)
    mobi.init_ethercat()
    mobi.driver._state = PlatformDriverState.ACTIVE  # force to active state so controller gets executed

    wheel_positions = [[] for _ in range(4)]

    plt.grid(True)
    plt.legend()
    plt.gca().set_aspect("equal")
    plt.xlim(-2.1, 2.1)
    plt.ylim(-2.1, 2.1)

    while True:
        mobi.step()

        # Store positions
        for i in range(4):
            wheel_positions[i].append([mobi.driver._cpc._current_position[i].x, mobi.driver._cpc._current_position[i].y])

        # Plot positions
        for i in range(4):
            plt.scatter(
                [dp[0] for dp in wheel_positions[i][-5:]],
                [dp[1] for dp in wheel_positions[i][-5:]],
                [j * 4 for j in range(min(len(wheel_positions[i]), 5))],
                marker="o",
                label=f"wheel {i}",
            )

        plt.pause(0.050)


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
