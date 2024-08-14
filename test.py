import math

import matplotlib.pyplot as plt


def get_shortest_angle(angle1: float, angle2: float) -> float:
    return math.atan2(math.sin(angle1 - angle2), math.cos(angle1 - angle2))


def sign(a):
    return 1 if a >= 0 else -1


target_pivot_angle = math.pi / 4

data_angles = []
data_forces = []
data_delta_forces = []

for raw_pivot_encoder in [2 * math.pi * i / 100 for i in range(100)]:
    angle_error = get_shortest_angle(target_pivot_angle, raw_pivot_encoder)

    force = math.cos(angle_error) ** 2
    force *= 1 if abs(angle_error) < math.pi / 2 else -1

    delta_force = math.sin(angle_error) ** 2 * sign(angle_error)
    delta_force *= 1 if abs(angle_error) < math.pi / 2 else -1

    data_angles.append(raw_pivot_encoder)
    data_forces.append(force)
    data_delta_forces.append(delta_force)

plt.plot(data_angles, data_forces, label="common force")
plt.plot(data_angles, data_delta_forces, label="differential force")
plt.grid(True)
plt.legend()
plt.show()
