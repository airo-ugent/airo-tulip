import random

import matplotlib.pyplot as plt
from airo_tulip.controllers.compliant_controller import CompliantController
from airo_tulip.structs import WheelConfig


def test():
    # Init stuff
    wheel_configs = create_wheel_configs()
    cc = CompliantController(wheel_configs)

    # Init timeseries outputs
    ts_time = []
    ts_encoder = []
    ts_velocity = []
    ts_position = []
    ts_torque = []

    # Test control loop
    encoders = [[random.random(), random.random(), random.random()] for _ in range(len(wheel_configs))]
    velocity = [0.0] * len(wheel_configs)
    position = [0.0] * len(wheel_configs)
    time = 0.0
    delta_time = 0.050

    while time < 5.0:
        for i in range(len(wheel_configs)):
            # Calculate torque using controller
            t_r, t_l = cc.calculate_wheel_target_torque(i, encoders[i], delta_time)
            print(f"wheel {i} torque_r {t_r} torque_l {t_l}")

            if time < 1.0:
                # Simulate pushing of robot
                position_old = position[i]
                position[i] += 1.0 * delta_time
                encoders[i][0] += (position[i] - position_old) / (cc._wheel_diameter / 2)
                encoders[i][1] += (position[i] - position_old) / (cc._wheel_diameter / 2)
            else:
                # Simulate free robot movement
                position_old = position[i]
                mass = 0.5
                acceleration = (t_r + t_l) / (cc._wheel_diameter / 2)
                velocity[i] += acceleration / mass * delta_time
                position[i] += velocity[i] * delta_time
                encoders[i][0] += (position[i] - position_old) / (cc._wheel_diameter / 2)
                encoders[i][1] += (position[i] - position_old) / (cc._wheel_diameter / 2)
            print(f"wheel {i} encoder_r {encoders[i][0]} encoder_l {encoders[i][1]}")

            if i == 0:
                ts_time.append(time)
                ts_encoder.append(encoders[i][0])
                ts_velocity.append(velocity[i])
                ts_position.append(position[i])
                ts_torque.append(t_r)

        time += delta_time

    # Create subplots
    fig, axs = plt.subplots(2, 2)

    # Plot encoder data
    axs[0, 0].plot(ts_time, ts_encoder)
    axs[0, 0].set_title("Encoder")
    axs[0, 0].grid(True)

    # Plot velocity data
    axs[0, 1].plot(ts_time, ts_velocity)
    axs[0, 1].set_title("Velocity")
    axs[0, 1].grid(True)

    # Plot position data
    axs[1, 0].plot(ts_time, ts_position)
    axs[1, 0].set_title("Position")
    axs[1, 0].grid(True)

    # Plot torque data
    axs[1, 1].plot(ts_time, ts_torque)
    axs[1, 1].set_title("Torque")
    axs[1, 1].grid(True)

    plt.tight_layout()
    plt.show()


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
