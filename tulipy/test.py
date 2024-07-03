import time

from tulipy.ethercat_master import EtherCATMaster
from tulipy.platform_driver import PlatformDriver
from tulipy.structs import WheelConfig

def test():
    # Init stuff
    wheel_configs = create_wheel_configs()
    driver = PlatformDriver(wheel_configs)
    ecm = EtherCATMaster(driver)
    ecm.init_ethercat()

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 1:
        ecm.loop()
        time.sleep(0.050)

    # Set target velocity
    driver.set_platform_target_velocity(1.0, 0.0, 0.0)

    # Wait one second
    time_start = time.time()
    while time.time() - time_start < 1:
        ecm.loop()
        time.sleep(0.050)

    # Set zero target velocity
    driver.set_platform_target_velocity(0.0, 0.0, 0.0)

    # Loop indefinitely
    while True:
        ecm.loop()
        time.sleep(0.050)
        

def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig()
    wc0.ethercat_number = 3
    wc0.x = 0.233
    wc0.y = 0.1165
    wc0.a = 1.57
    wheel_configs.append(wc0)

    wc1 = WheelConfig()
    wc1.ethercat_number = 5
    wc1.x = 0.233
    wc1.y = -0.1165
    wc1.a = 1.57
    wheel_configs.append(wc1)

    wc2 = WheelConfig()
    wc2.ethercat_number = 7
    wc2.x = -0.233
    wc2.y = -0.1165
    wc2.a = -1.57
    wheel_configs.append(wc2)

    wc3 = WheelConfig()
    wc3.ethercat_number = 9
    wc3.x = -0.233
    wc3.y = 0.1165
    wc3.a = 1.57
    wheel_configs.append(wc3)

    return wheel_configs

if __name__ == "__main__":
    test()

