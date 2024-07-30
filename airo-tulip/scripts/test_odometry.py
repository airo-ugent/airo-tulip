import time

from airo_tulip.server.kelo_robile import KELORobile

def test():
    mobi = KELORobile("localhost", 49789)

    odom = mobi.get_odometry()
    print(f"Start odometry (should be 0 vector): {odom}")

    mobi.set_platform_velocity_target(0.2, 0.0, 0.0, instantaneous=True)
    time.sleep(3)  # movement should timeout

    odom = mobi.get_odometry()
    print(f"End odometry (Should be close to [0.2, 0.0, 0.0]): {odom}")

    mobi.stop_server()


if __name__ == "__main__":
    test()
