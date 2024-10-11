"""Constants taken directly from KELO:
https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/src/PlatformDriver.cpp"""

WHEEL_DISTANCE = 0.0775
WHEEL_DIAMETER = 0.104
WHEEL_RADIUS = 0.5 * WHEEL_DIAMETER
CASTOR_OFFSET = 0.01
CURRENT_STOP = 1
CURRENT_DRIVE = 20
MAX_V_LIN = 1.5
MAX_V_A = 1.0
MAX_V_LIN_ACC = 0.0025  # per millisecond, same value for deceleration
MAX_ANGLE_ACC = 0.01  # at vlin=0, per msec, same value for deceleration
MAX_V_A_ACC = 0.01  # per millisecond, same value for deceleration
WHEEL_SET_POINT_MIN = 0.01
WHEEL_SET_POINT_MAX = 35.0
