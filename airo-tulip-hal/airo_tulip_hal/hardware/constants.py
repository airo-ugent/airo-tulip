"""Constants taken directly from KELO:
https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/src/PlatformDriver.cpp"""

# Re-exported from the shared API contract so the driver and the (HAL-free) client agree on the limits.
from airo_tulip.api.types import MAX_PLATFORM_ANGULAR_VELOCITY, MAX_PLATFORM_LINEAR_VELOCITY  # noqa: F401

# Drive geometry used by the odometry / pose estimation (see platform_monitor.py). These match the
# values used by KELO's odometry in PlatformDriverROS.cpp: s_w = 0.01, d_w = 0.0775, r_w = 0.0524.
WHEEL_DISTANCE = 0.0775
WHEEL_DIAMETER = 0.1048  # so WHEEL_RADIUS == 0.0524, matching KELO's odometry wheel radius (r_w).
WHEEL_RADIUS = 0.5 * WHEEL_DIAMETER
CASTOR_OFFSET = 0.01

# Drive geometry used by the velocity controller (see controllers/controller.py). These match KELO's
# WheelModel.h defaults (KELOdrive105): diameter = 0.105, casteroffset = 0.010, wheeldistance = 0.080.
# CONTROLLER_WHEEL_DISTANCE is the *same physical quantity* as WHEEL_DISTANCE above (lateral spacing
# between the left and right hub wheel of a single drive) but KELO deliberately uses a different value
# in the control path (0.080) than in the odometry path (0.0775), so the two are kept separate.
# NOTE: this was 0.055 from the original (untested) C++->Python port in commit 87da033, which appears
# to be a transcription error: diameter and caster were copied correctly from WheelModel.h but the
# wheel distance was not. Corrected to 0.080 to match the C++ ground truth.
CONTROLLER_WHEEL_DIAMETER = 0.105
CONTROLLER_WHEEL_DISTANCE = 0.080
CONTROLLER_CASTER_OFFSET = CASTOR_OFFSET

CURRENT_STOP = 1
CURRENT_DRIVE = 20

# Safety limits (MAX_PLATFORM_LINEAR_VELOCITY, MAX_PLATFORM_ANGULAR_VELOCITY) are imported above from
# the shared API contract and enforced on incoming platform velocity targets (see platform_driver.py).

WHEEL_SET_POINT_MIN = 0.01
WHEEL_SET_POINT_MAX = 35.0
