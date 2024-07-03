import time

from tulipy.ethercat_master import EtherCATMaster
from tulipy.platform_driver import PlatformDriver
from tulipy.structs import WheelConfig

def test():
    # Init stuff
    device = "eno1"
    wheel_configs = create_wheel_configs()
    ecm = EtherCATMaster(device)
    driver = PlatformDriver(ecm.get_master(), wheel_configs)
    ecm.set_driver(driver)
    ecm.init_ethercat()

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 1:
        ecm.loop()
        time.sleep(0.050)

    # Set target velocity
    driver.set_platform_velocity_target(1.0, 0.0, 0.0)

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 100:
        ecm.loop()
        time.sleep(0.050)

    # Set zero target velocity
    driver.set_platform_velocity_target(0.0, 0.0, 0.0)

    # Loop indefinitely
    while True:
        ecm.loop()
        time.sleep(0.050)
        

def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig(
        ethercat_number = 3,
        x = 0.233,
        y = 0.1165,
        a = 1.57
    )
    wheel_configs.append(wc0)

    wc1 = WheelConfig(
        ethercat_number = 5,
        x = 0.233,
        y = -0.1165,
        a = 1.57
    )
    wheel_configs.append(wc1)

    wc2 = WheelConfig(
        ethercat_number = 7,
        x = -0.233,
        y = -0.1165,
        a = -1.57
    )
    wheel_configs.append(wc2)

    wc3 = WheelConfig(
        ethercat_number = 9,
        x = -0.233,
        y = 0.1165,
        a = 1.57
    )
    wheel_configs.append(wc3)

    return wheel_configs

if __name__ == "__main__":
    test()

