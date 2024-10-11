import math


def clip(value: float, maximum: float, minimum: float) -> float:
    """Clip a value between a maximum and a minimum value."""
    return min(max(value, minimum), maximum)


def clip_angle(angle: float) -> float:
    """Clip an angle between -pi and pi."""
    if angle < -math.pi:
        return angle + (2 * math.pi)
    elif angle > math.pi:
        return angle - (2 * math.pi)
    else:
        return angle


def get_shortest_angle(angle1: float, angle2: float) -> float:
    """Get the shortest angle between two angles."""
    return math.atan2(math.sin(angle1 - angle2), math.cos(angle1 - angle2))


def sign(a: float) -> float:
    """Get the sign of a number. For 0, returns 1.0"""
    return 1.0 if a >= 0 else -1.0
