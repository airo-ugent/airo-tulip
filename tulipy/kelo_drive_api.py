# See: https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/include/kelo_tulip/KeloDriveAPI.h#L170

import ctypes

class RxPDO1(ctypes.Structure):
    _pack_ = 1,
    _fields_ = [
        ('command1', ctypes.c_uint16),  # Command bits as defined in COM1_
        ('command2', ctypes.c_uint16),  # Command bits as defined in COM2_
        ('setpoint1', ctypes.c_float),  # Setpoint 1
        ('setpoint2', ctypes.c_float),  # Setpoint 2
        ('limit1_p', ctypes.c_float),   # Upper limit 1
        ('limit1_n', ctypes.c_float),   # Lower limit 1
        ('limit2_p', ctypes.c_float),   # Upper limit 2
        ('limit2_n', ctypes.c_float),   # Lower limit 2
        ('timestamp', ctypes.c_uint64)  # EtherCAT timestamp (ns) setpoint execution
    ]
