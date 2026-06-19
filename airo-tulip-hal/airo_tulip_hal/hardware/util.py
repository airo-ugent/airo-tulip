import math


def clip(value: float, maximum: float, minimum: float) -> float:
    """Clip a value between a maximum and a minimum value."""
    return min(max(value, minimum), maximum)


def clip_angle(angle: float) -> float:
    """Normalize an angle to the range [-pi, pi]. Handles angles that are multiple revolutions out of range."""
    while angle < -math.pi:
        angle += math.tau
    while angle > math.pi:
        angle -= math.tau
    return angle


def get_shortest_angle(angle1: float, angle2: float) -> float:
    """Get the shortest angle between two angles."""
    return math.atan2(math.sin(angle1 - angle2), math.cos(angle1 - angle2))
