from dataclasses import dataclass


@dataclass
class SetPlatformVelocityTarget:
    vel_x: float
    vel_y: float
    vel_a: float
