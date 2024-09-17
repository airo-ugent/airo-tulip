import numpy as np
from airo_robots.manipulators.hardware.ur_rtde import URrtde

robot = URrtde("localhost", URrtde.UR3E_CONFIG)

start_pose_joints = np.array([1.183442, -1.1536765, 1.06586181, -0.21244033, 1.18598807, 3.14284897])
robot.move_to_joint_configuration(start_pose_joints).wait()

start_pose = np.zeros((4, 4))
start_pose[:, 0] = np.array([-1.0, 0.0, 0.0, 0.0])
start_pose[:, 1] = np.array([0.0, 0.0, -1.0, 0.0])
start_pose[:, 2] = np.array([0.0, -1.0, 0.0, 0.0])
start_pose[:, 3] = np.array([-0.11, -0.7, 0.35, 1.0])
robot.move_to_tcp_pose(start_pose).wait()

input()

X_B_GLASS = np.zeros((4, 4))
X_B_GLASS[:, 0] = np.array([-1.0, 0.0, 0.0, 0.0])
X_B_GLASS[:, 1] = np.array([0.0, 0.0, 1.0, 0.0])
X_B_GLASS[:, 2] = np.array([0.0, 1.0, 0.0, 0.0])
X_B_GLASS[:, 3] = np.array([0.0, -0.7, 0.35, 1.0])

X_GLASS_B = np.linalg.inv(X_B_GLASS)

for a in np.linspace(0.0, np.pi * 3 / 8, 5, endpoint=True):
    R1 = np.array(
        [
            [np.cos(a), -np.sin(a), 0.0, 0.0],
            [np.sin(a), np.cos(a), 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    R2 = np.array(
        [
            [np.cos(a), np.sin(a), 0.0, 0.0],
            [-np.sin(a), np.cos(a), 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    tcp_pose = X_B_GLASS @ R1 @ X_GLASS_B @ start_pose @ R2
    print(tcp_pose)

    robot.move_to_tcp_pose(tcp_pose).wait()
