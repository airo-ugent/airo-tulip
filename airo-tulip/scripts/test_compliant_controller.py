import copy
import math
import random

import matplotlib.pyplot as plt
from airo_tulip.controllers.compliant_controller import CompliantController
from airo_tulip.structs import Attitude2DType, Point2D, WheelConfig

# Init timeseries outputs
ts_time = []
ts_encoders = []
ts_velocity = []
ts_position = []
ts_position_estimated = []
ts_torque = []
wheel_positions = [[] for _ in range(4)]
wheel_torques = [[] for _ in range(4)]


def test():
    # Init stuff
    wheel_configs = create_wheel_configs()
    cc = CompliantController(wheel_configs)

    # Test control loop
    encoders = [[random.random(), random.random(), random.random()] for _ in range(len(wheel_configs))]
    velocity = [Point2D() for _ in range(len(wheel_configs))]
    position = [Attitude2DType(wc.x, wc.y, random.random()) for wc in wheel_configs]
    time = 0.0
    delta_time = 0.050

    while time < 5.0:
        for i in range(len(wheel_configs)):
            # Calculate torque using controller
            t_r, t_l = cc.calculate_wheel_target_torque(i, encoders[i], delta_time)
            print(f"wheel {i} torque_r {t_r} torque_l {t_l}")

            position_old = copy.copy(position[i])
            center = Point2D(sum([p.x for p in position]) / 4, sum([p.y for p in position]) / 4)
            angle_platform = math.atan2(position[i].y - center.y, position[i].x - center.x) - math.atan2(
                wheel_configs[i].y, wheel_configs[i].x
            )
            if time < 1.0:
                # Simulate pushing of robot to positive x
                position[i].x += 1.0 * delta_time
                position[i].a = (
                    math.atan2(position[i].y - position_old.y, position[i].x - position_old.x)
                    - angle_platform
                    - wheel_configs[i].a
                )
            # elif time < 2.0:
            #    # Simulate pushing of robot to positive y
            #    position[i].y += 1.0 * delta_time
            #    position[i].a = math.atan2(position[i].y - position_old.y, position[i].x - position_old.x) - angle_platform - wheel_configs[i].a
            else:
                # Simulate free robot movement
                mass = 0.5
                acc_comm = (t_r + t_l) / (cc._wheel_diameter / 2) / mass
                acc_diff = (-t_r + t_l) / (cc._wheel_diameter / 2) / mass

                center = Point2D(sum([p.x for p in position]) / 4, sum([p.y for p in position]) / 4)
                angle_platform = math.atan2(position[i].y - center.y, position[i].x - center.x) - math.atan2(
                    wheel_configs[i].y, wheel_configs[i].x
                )
                angle = angle_platform + wheel_configs[i].a + position[i].a

                acc_x = acc_comm * math.cos(angle)
                acc_y = acc_comm * math.sin(angle)

                velocity[i].x += acc_x * delta_time
                velocity[i].y += acc_y * delta_time
                position[i].x += velocity[i].x * delta_time
                position[i].y += velocity[i].y * delta_time
                position[i].a = (
                    math.atan2(position[i].y - position_old.y, position[i].x - position_old.x)
                    - angle_platform
                    - wheel_configs[i].a
                    + acc_diff * delta_time
                )

            # Simulate sensors
            encoders[i][0] += -math.sqrt(
                (position[i].x - position_old.x) ** 2 + (position[i].y - position_old.y) ** 2
            ) / (cc._wheel_diameter / 2)
            # encoders[i][0] %= 2*math.pi
            encoders[i][1] += math.sqrt(
                (position[i].x - position_old.x) ** 2 + (position[i].y - position_old.y) ** 2
            ) / (cc._wheel_diameter / 2)
            # encoders[i][1] %= 2*math.pi
            encoders[i][2] = position[i].a
            print(f"wheel {i} encoder_r {encoders[i][0]} encoder_l {encoders[i][1]} encoder_p {encoders[i][2]}")

            if i == 0:
                ts_time.append(time)
                ts_encoders.append(encoders[i].copy())
                ts_velocity.append([velocity[i].x, velocity[i].y])
                ts_position.append([position[i].x, position[i].y])
                ts_position_estimated.append([cc._current_position[i].x, cc._current_position[i].y])
                ts_torque.append([t_r, t_l])

            wheel_positions[i].append([position[i].x, position[i].y, position[i].a])
            wheel_torques[i].append([t_r, t_l])

        time += delta_time

        plot_platform()

    plot_results()


def plot_results():
    # Create subplots
    fig, axs = plt.subplots(2, 2)

    # Plot encoder data
    axs[0, 0].plot(ts_time, [dp[0] for dp in ts_encoders], label="right")
    axs[0, 0].plot(ts_time, [dp[1] for dp in ts_encoders], label="left")
    axs[0, 0].plot(ts_time, [dp[2] for dp in ts_encoders], label="pivot")
    axs[0, 0].set_title("Encoders")
    axs[0, 0].legend()
    axs[0, 0].grid(True)

    # Plot velocity data
    axs[0, 1].plot(ts_time, [dp[0] for dp in ts_velocity], label="x")
    axs[0, 1].plot(ts_time, [dp[1] for dp in ts_velocity], label="y")
    axs[0, 1].set_title("Velocity")
    axs[0, 1].legend()
    axs[0, 1].grid(True)

    # Plot position data
    axs[1, 0].plot(ts_time, [dp[0] for dp in ts_position], label="x")
    axs[1, 0].plot(ts_time, [dp[1] for dp in ts_position], label="y")
    axs[1, 0].plot(ts_time, [dp[0] for dp in ts_position_estimated], label="x est")
    axs[1, 0].plot(ts_time, [dp[1] for dp in ts_position_estimated], label="y est")
    axs[1, 0].set_title("Position")
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    # Plot torque data
    axs[1, 1].plot(ts_time, [dp[0] for dp in ts_torque], label="right")
    axs[1, 1].plot(ts_time, [dp[1] for dp in ts_torque], label="left")
    axs[1, 1].set_title("Torque")
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    plt.tight_layout()
    plt.show()

    # Plot wheel positions
    for i in range(4):
        plt.scatter(
            [dp[0] for dp in wheel_positions[i]],
            [dp[1] for dp in wheel_positions[i]],
            [j * 50 / len(wheel_positions[i]) for j in range(len(wheel_positions[i]))],
            marker="o",
            label=f"wheel {i}",
        )
    plt.grid(True)
    plt.legend()
    plt.show()


def plot_platform():
    # Plot wheel positions
    for i in range(4):
        plt.scatter(
            [dp[0] for dp in wheel_positions[i]][-5:],
            [dp[1] for dp in wheel_positions[i]][-5:],
            [i * 4 for i in range(min(len(wheel_positions), 5))],
            marker="o",
            label=f"wheel {i}",
        )
        plt.arrow(
            wheel_positions[i][-1][0] - 0.050 * math.sin(wheel_positions[i][-1][2]),
            wheel_positions[i][-1][1] + 0.050 * math.cos(wheel_positions[i][-1][2]),
            wheel_torques[i][-1][0] * 10 * math.cos(wheel_positions[i][-1][2]),
            wheel_torques[i][-1][0] * 10 * math.sin(wheel_positions[i][-1][2]),
            width=0.02,
        )
        plt.arrow(
            wheel_positions[i][-1][0] + 0.050 * math.sin(wheel_positions[i][-1][2]),
            wheel_positions[i][-1][1] - 0.050 * math.cos(wheel_positions[i][-1][2]),
            wheel_torques[i][-1][1] * 10 * math.cos(wheel_positions[i][-1][2]),
            wheel_torques[i][-1][1] * 10 * math.sin(wheel_positions[i][-1][2]),
            width=0.02,
        )
    plt.grid(True)
    plt.legend()
    plt.gca().set_aspect("equal")
    plt.xlim(-2.1, 2.1)
    plt.ylim(-2.1, 2.1)
    plt.show()


def create_wheel_configs():
    wheel_configs = []

    wc0 = WheelConfig(ethercat_number=3, x=0.233, y=0.1165, a=1.57)
    wheel_configs.append(wc0)

    wc1 = WheelConfig(ethercat_number=5, x=0.233, y=-0.1165, a=1.57)
    wheel_configs.append(wc1)

    wc2 = WheelConfig(ethercat_number=7, x=-0.233, y=-0.1165, a=1.57)
    wheel_configs.append(wc2)

    wc3 = WheelConfig(ethercat_number=9, x=-0.233, y=0.1165, a=1.57)
    wheel_configs.append(wc3)

    return wheel_configs


if __name__ == "__main__":
    test()
