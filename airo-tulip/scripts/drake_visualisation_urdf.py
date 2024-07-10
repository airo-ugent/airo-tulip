import numpy as np
import airo_models
from pydrake.math import RigidTransform, RollPitchYaw
from pydrake.geometry import Meshcat
from pydrake.geometry import MeshcatVisualizer
from pydrake.planning import RobotDiagramBuilder

robot_diagram_builder = RobotDiagramBuilder()
scene_graph = robot_diagram_builder.scene_graph()
plant = robot_diagram_builder.plant()
builder = robot_diagram_builder.builder()
plant = robot_diagram_builder.plant()
parser = robot_diagram_builder.parser()
parser.SetAutoRenaming(True)

meshcat = Meshcat()
visualizer = MeshcatVisualizer.AddToBuilder(builder, scene_graph, meshcat)

# Load URDF files
ur5e_urdf_path = airo_models.get_urdf_path("ur5e")

# Weld some frames together
world_frame = plant.world_frame()

brick_size = 0.233
brick_size_half = 0.5 *brick_size

drive_transforms = [
    RigidTransform(p=[-brick_size_half, -brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0])),
    RigidTransform(p=[-brick_size_half, brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0])),
    RigidTransform(p=[-brick_size * 2 - brick_size_half, -brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0])),
    RigidTransform(p=[-brick_size * 2 - brick_size_half, brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0])),
]

# robot_transform: relative to world
# drive_transforms: relative to robot_transform
for drive_index, drive_transform in enumerate(drive_transforms):
    brick_index = parser.AddModels("../../urdf/wheel_brick.urdf")[0]
    brick_frame = plant.GetFrameByName("base_link", brick_index)
    plant.WeldFrames(world_frame, brick_frame, drive_transform)

battery_transform = RigidTransform(p=[-brick_size_half - brick_size, brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0]))
battery_index = parser.AddModels("../../urdf/battery_brick.urdf")[0]
battery_frame = plant.GetFrameByName("base_link", battery_index)
plant.WeldFrames(world_frame, battery_frame, battery_transform)

cpu_transform = RigidTransform(p=[-brick_size_half - brick_size, -brick_size_half, 0], rpy=RollPitchYaw([0, 0, 0]))
cpu_index = parser.AddModels("../../urdf/cpu_brick.urdf")[0]
cpu_frame = plant.GetFrameByName("base_link", cpu_index)
plant.WeldFrames(world_frame, cpu_frame, cpu_transform)

side_height = 0.43
side_height_half = 0.5 * side_height
side_length = 0.69
side_length_half = 0.5 * side_length
side_transforms = [
    RigidTransform(p=[-side_length_half, -brick_size, side_height_half]),
    RigidTransform(p=[-side_length_half, brick_size, side_height_half]),
]

for side_transform in side_transforms:
    side_urdf_path = airo_models.box_urdf_path([side_length, 0.03, side_height], "side")
    side_index = parser.AddModels(side_urdf_path)[0]
    side_frame = plant.GetFrameByName("base_link", side_index)
    plant.WeldFrames(world_frame, side_frame, side_transform)

roof_length = side_length
roof_length_half = 0.5 * roof_length
roof_width = 0.525
roof_width_half = 0.5 * roof_width
roof_thickness = 0.03
roof_thickness_half = 0.5 * roof_thickness
roof_transform = RigidTransform(p=[-roof_length_half, 0, side_height + roof_thickness_half])

roof_urdf_path = airo_models.box_urdf_path([roof_length, roof_width, 0.03], "roof")
roof_index = parser.AddModels(roof_urdf_path)[0]
roof_frame = plant.GetFrameByName("base_link", roof_index)
plant.WeldFrames(world_frame, roof_frame, roof_transform)

ur5e_transform = RigidTransform(p=[-0.105, 0, side_height + roof_thickness], rpy=RollPitchYaw([0, 0, -np.pi / 2]))
ur5e_index = parser.AddModels(ur5e_urdf_path)[0]
ur5e_frame = plant.GetFrameByName("base_link", ur5e_index)
plant.WeldFrames(world_frame, ur5e_frame, ur5e_transform)

# Finishing and visualizing
diagram = robot_diagram_builder.Build()
context = diagram.CreateDefaultContext()
plant_context = plant.GetMyContextFromRoot(context)
diagram.ForcedPublish(context)

while True:
    pass
