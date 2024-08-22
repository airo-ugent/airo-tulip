import matplotlib.pyplot as plt
import numpy as np
from pykalman import UnscentedKalmanFilter


# Setup kalman filter
def transition_function(state, noise):
    dt = 0.1
    F = np.eye(6)
    F[0:3, 3:6] = np.eye(3) * dt
    return np.dot(F, state) + noise


def observation_function(state, noise):
    dt = 0.1
    R = 0.232
    [p_x, p_y, p_a, v_x, v_y, v_a] = state[0:6]

    flow_x = v_x * np.cos(p_a) + v_y * np.sin(p_a) - R * v_a * dt
    flow_y = -v_x * np.sin(p_a) + v_y * np.cos(p_a)

    return np.array([flow_x, flow_y, p_x, p_y, p_a, v_x, v_y, v_a]) + noise


transition_covariance = np.eye(6)
observation_covariance = np.eye(8)
initial_state_mean = np.array([0] * 6)
initial_state_covariance = np.eye(6)

kf = UnscentedKalmanFilter(
    transition_function,
    observation_function,
    transition_covariance,
    observation_covariance,
    initial_state_mean,
    initial_state_covariance,
)

observations = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [2, 0, 2, 0, 0, 3, 0, 0],
    [2, 0, 4, 0, 0, 3, 1, 0],
    [3, 0, 6, 1, 0, 3, 1, 0],
    [0, 0, 9, 1, 0, 1, 1, 0],
    [0, 0, 9, 1, 0, 0, 0, 0],
    [1, 0, 8, 0, 0, 0, 0, 0],
    [0, 0, 9, 1, 0, 0, 0, 0],
    [0, 1, 9, 1, 0, 0, 0, 0],
    [0, 0, 8, 1, 0, 0, 0, 0],
    [0, 0, 8, 2, 0, 0, 0, 0],
    [0, 0, 9, 1, 0, 0, 0, 0],
    [0, 0, 9, 0, 0, 0, 0, 0],
    [0, 0, 9, 1, 0, 0, 0, 0],
]

filtered_state_mean = initial_state_mean
filtered_state_covariance = initial_state_covariance
means = []
for observation in observations:
    filtered_state_mean, filtered_state_covariance = kf.filter_update(
        filtered_state_mean, filtered_state_covariance, observation
    )
    means.append(filtered_state_mean)

plt.plot(means, label="filtered")
plt.grid(True)
plt.legend()
plt.show()
