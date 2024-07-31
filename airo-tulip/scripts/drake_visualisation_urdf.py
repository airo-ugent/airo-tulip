from typing import List

import airo_models
import numpy as np
from airo_tulip.structs import Point2D
from pydrake.geometry import Meshcat
from pydrake.geometry import MeshcatVisualizer
from pydrake.math import RigidTransform, RollPitchYaw
from pydrake.multibody.plant import MultibodyPlant
from pydrake.multibody.tree import RigidBodyFrame, PlanarJoint
from pydrake.planning import RobotDiagramBuilder

robot_diagram_builder = RobotDiagramBuilder()
scene_graph = robot_diagram_builder.scene_graph()
plant = robot_diagram_builder.plant()
builder = robot_diagram_builder.builder()
parser = robot_diagram_builder.parser()
parser.SetAutoRenaming(True)

meshcat = Meshcat()
visualizer = MeshcatVisualizer.AddToBuilder(builder, scene_graph, meshcat)

# Weld some frames together
world_frame = plant.world_frame()


def create_mobile_robot(plant: MultibodyPlant, robot_root_frame: RigidBodyFrame, drive_positions: List[Point2D],
                        battery_position: Point2D,
                        cpu_position: Point2D,
                        side_height: float, side_length: float, roof_width: float, roof_thickness: float,
                        ur5e_position: Point2D, ur5e_yaw: float):
    """Create a mobile robot from a set of drive and other brick positions, and weld a UR5e robot arm on it.

    This function assumes that the robot's frame is +X forward, +Y left, +Z up (right handed).

    Args:
        plant: The MultibodyPlant.
        robot_root_frame: The robot's root frame.
        drive_positions: A list of 2D positions of the drive bricks, relative to the brick size and root frame.
        battery_position: A 2D position of the battery brick, relative to the brick size and root frame.
        cpu_position: A 2D position of the CPU brick, relative to the brick size and root frame.
        side_height: The height of the mobile robot's side.
        side_length: The length (along X) of the mobile robot.
        roof_width: The width (along Y) of the mobile robot.
        roof_thickness: The thickness of the roof.
        ur5e_position: A 2D position of the robot arm that is mounted on the roof.
        ur5e_yaw: Yaw (radians) of the robot arm's mount. +Y is the side of the power cable.
        """
    brick_size = 0.233  # From technical specs.

    drive_transforms = [
        RigidTransform(p=[brick_size * p.x, brick_size * p.y, 0], rpy=RollPitchYaw([0, 0, 0])) for p in drive_positions
    ]

    # robot_transform: relative to world
    # drive_transforms: relative to robot_transform
    for drive_index, drive_transform in enumerate(drive_transforms):
        brick_index = parser.AddModels(airo_models.get_urdf_path("kelo_robile_wheel"))[0]
        brick_frame = plant.GetFrameByName("base_link", brick_index)
        plant.WeldFrames(robot_root_frame, brick_frame, drive_transform)

    battery_transform = RigidTransform(p=[brick_size * battery_position.x, brick_size * battery_position.y, 0],
                                       rpy=RollPitchYaw([0, 0, 0]))
    battery_index = parser.AddModels(airo_models.get_urdf_path("kelo_robile_battery"))[0]
    battery_frame = plant.GetFrameByName("base_link", battery_index)
    plant.WeldFrames(robot_root_frame, battery_frame, battery_transform)

    cpu_transform = RigidTransform(p=[brick_size * cpu_position.x, brick_size * cpu_position.y, 0],
                                   rpy=RollPitchYaw([0, 0, 0]))
    cpu_index = parser.AddModels(airo_models.get_urdf_path("kelo_robile_cpu"))[0]
    cpu_frame = plant.GetFrameByName("base_link", cpu_index)
    plant.WeldFrames(robot_root_frame, cpu_frame, cpu_transform)

    side_height_half = 0.5 * side_height
    side_length_half = 0.5 * side_length
    side_transforms = [
        RigidTransform(p=[-side_length_half, -brick_size, side_height_half]),
        RigidTransform(p=[-side_length_half, brick_size, side_height_half]),
    ]

    for side_transform in side_transforms:
        side_urdf_path = airo_models.box_urdf_path([side_length, 0.03, side_height], "side")
        side_index = parser.AddModels(side_urdf_path)[0]
        side_frame = plant.GetFrameByName("base_link", side_index)
        plant.WeldFrames(robot_root_frame, side_frame, side_transform)

    roof_length = side_length
    roof_length_half = 0.5 * roof_length
    roof_thickness_half = 0.5 * roof_thickness
    roof_transform = RigidTransform(p=[-roof_length_half, 0, side_height + roof_thickness_half])

    roof_urdf_path = airo_models.box_urdf_path([roof_length, roof_width, 0.03], "roof")
    roof_index = parser.AddModels(roof_urdf_path)[0]
    roof_frame = plant.GetFrameByName("base_link", roof_index)
    plant.WeldFrames(robot_root_frame, roof_frame, roof_transform)

    ur5e_transform = RigidTransform(p=[ur5e_position.x, ur5e_position.y, side_height + roof_thickness],
                                    rpy=RollPitchYaw([0, 0, ur5e_yaw]))
    ur5e_index = parser.AddModels(airo_models.get_urdf_path("ur5e"))[0]
    ur5e_frame = plant.GetFrameByName("base_link", ur5e_index)
    plant.WeldFrames(robot_root_frame, ur5e_frame, ur5e_transform)


mobi_model_index = parser.AddModels(airo_models.get_urdf_path("kelo_robile"))[0]
mobi_frame = plant.GetFrameByName("base_link", mobi_model_index)

create_mobile_robot(plant, mobi_frame,
                    [Point2D(-0.5, -0.5), Point2D(-0.5, 0.5), Point2D(-2.5, -0.5), Point2D(-2.5, 0.5)],
                    Point2D(-1.5, 0.5), Point2D(-1.5, -0.5), 0.43, 0.69, 0.525, 0.03, Point2D(-0.105, 0), -np.pi / 2)

platform_planar_joint = PlanarJoint("mobi_joint", world_frame, mobi_frame)
platform_planar_joint.set_velocity_limits([0, 0, 0], [1.5, 1.5, np.pi / 8])
plant.AddJoint(platform_planar_joint)

# Finishing and visualizing
diagram = robot_diagram_builder.Build()
context = diagram.CreateDefaultContext()
plant_context = plant.GetMyContextFromRoot(context)
diagram.ForcedPublish(context)

# The first three positions represent the platform's pose (x, y, theta). The last six represent the UR's configuration.
plant.SetPositions(plant_context, [0.5, 0.5, np.pi, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
diagram.ForcedPublish(context)

print(plant.GetPositions(plant_context))

while True:
    pass
