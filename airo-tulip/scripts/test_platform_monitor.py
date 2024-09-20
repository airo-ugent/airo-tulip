import time

from airo_tulip.platform_driver import PlatformDriverType
from airo_tulip.robile_platform import RobilePlatform
from airo_tulip.structs import WheelConfig


def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()
    mobi = RobilePlatform(device, wheel_configs, PlatformDriverType.VELOCITY)
    mobi.init_ethercat()
    mobi.driver.set_platform_velocity_target(0.0, 0.1, 0.0, timeout=2.0, only_align_drives=True)

    # Loop for 2.0 seconds
    start = time.time()
    while time.time() - start < 2.0:
        mobi.step()
        time.sleep(0.050)

    mobi.driver.set_platform_velocity_target(0.0, 0.2, 0.0, timeout=3.0)

    # Loop indefinitely
    while True:
        mobi.step()
        fancy_print_sensors(mobi.monitor)
        time.sleep(0.050)


def fancy_print_sensors(monitor):
    #for i in range(4):
    #    print(f"accel {i} ", monitor.get_acceleration(i))
    #    print(f"gyro {i} ", monitor.get_gyro(i))
    #    print(f"enc {i} vel ", monitor.get_velocity(i))
    print("flow ", monitor.get_flow())
    print("odom pose ", monitor._odometry_pose)
    #print("odom vel ", monitor._odometry_velocity)
    print("pose ", monitor.get_estimated_robot_pose())
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
