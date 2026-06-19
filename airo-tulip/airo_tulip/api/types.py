"""Shared types that form part of the client/server API contract.

These live in the lightweight ``airo-tulip`` package (rather than in ``airo-tulip-hal``) so that a
client can depend on them without pulling in the hardware abstraction layer (and its ``pysoem``
dependency)."""

from enum import Enum

import numpy as np

Attitude2DType = np.ndarray
"""A (3,) np array representing a pose in 2D space with Cartesian coordinates, with `a` the angle measured from the X-axis."""


class PlatformDriverType(Enum):
    """Platform driver type (velocity or compliant modes)."""

    VELOCITY = 1
    COMPLIANT_WEAK = 2
    COMPLIANT_MODERATE = 3
    COMPLIANT_STRONG = 4
