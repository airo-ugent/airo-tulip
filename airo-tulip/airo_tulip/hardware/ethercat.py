import ctypes

STAT1_ENABLED1 = 0x0001
STAT1_ENABLED2 = 0x0002
STAT1_ENC_1_OK = 0x0004
STAT1_ENC_2_OK = 0x0008
STAT1_ENC_PIVOT_OK = 0x0010
STAT1_UNDERVOLTAGE = 0x0020
STAT1_OVERVOLTAGE = 0x0040
STAT1_OVERCURRENT_1 = 0x0080
STAT1_OVERCURRENT_2 = 0x0100
STAT1_OVERTEMP_1 = 0x0200
STAT1_OVERTEMP_2 = 0x0400
STAT1_ENABLED_GRIP = 0x0800
STAT1_INPOS_GRIP = 0x1000
STAT1_OVERLOAD_GRIP = 0x2000
STAT1_DETECT = 0x4000

STAT2_UNUSED = 0x0000


class RxPDO1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("command1", ctypes.c_uint16),  # Command bits as defined in COM1_
        ("command2", ctypes.c_uint16),  # Command bits as defined in COM2_
        ("setpoint1", ctypes.c_float),  # Setpoint 1
        ("setpoint2", ctypes.c_float),  # Setpoint 2
        ("limit1_p", ctypes.c_float),  # Upper limit 1
        ("limit1_n", ctypes.c_float),  # Lower limit 1
        ("limit2_p", ctypes.c_float),  # Upper limit 2
        ("limit2_n", ctypes.c_float),  # Lower limit 2
        ("timestamp", ctypes.c_uint64),  # EtherCAT timestamp (ns) setpoint execution
    ]


class TxPDO1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("status1", ctypes.c_uint16),  # Status bits as defined in STAT1_
        ("status2", ctypes.c_uint16),  # Status bits as defined in STAT2_
        ("sensor_ts", ctypes.c_uint64),  # EtherCAT timestamp (ns) on sensor acquisition
        ("setpoint_ts", ctypes.c_uint64),  # EtherCAT timestamp (ns) of last setpoint data
        ("encoder_1", ctypes.c_float),  # encoder 1 value in rad (no wrapping at 2PI)
        ("velocity_1", ctypes.c_float),  # encoder 1 velocity in rad/s
        ("current_1_d", ctypes.c_float),  # motor 1 current direct in amp
        ("current_1_q", ctypes.c_float),  # motor 1 current quadrature in amp
        ("current_1_u", ctypes.c_float),  # motor 1 current phase U in amp
        ("current_1_v", ctypes.c_float),  # motor 1 current phase V in amp
        ("current_1_w", ctypes.c_float),  # motor 1 current phase W in amp
        ("voltage_1", ctypes.c_float),  # motor 1 voltage from pwm in volts
        ("voltage_1_u", ctypes.c_float),  # motor 1 voltage from phase U in volts
        ("voltage_1_v", ctypes.c_float),  # motor 1 voltage from phase V in volts
        ("voltage_1_w", ctypes.c_float),  # motor 1 voltage from phase W in volts
        ("temperature_1", ctypes.c_float),  # motor 1 estimated temperature in K
        ("encoder_2", ctypes.c_float),  # encoder 2 value in rad (no wrapping at 2PI)
        ("velocity_2", ctypes.c_float),  # encoder 2 velocity in rad/s
        ("current_2_d", ctypes.c_float),  # motor 2 current direct in amp
        ("current_2_q", ctypes.c_float),  # motor 2 current quadrature in amp
        ("current_2_u", ctypes.c_float),  # motor 2 current phase U in amp
        ("current_2_v", ctypes.c_float),  # motor 2 current phase V in amp
        ("current_2_w", ctypes.c_float),  # motor 2 current phase W in amp
        ("voltage_2", ctypes.c_float),  # motor 2 voltage from pwm in volts
        ("voltage_2_u", ctypes.c_float),  # motor 2 voltage from phase U in volts
        ("voltage_2_v", ctypes.c_float),  # motor 2 voltage from phase V in volts
        ("voltage_2_w", ctypes.c_float),  # motor 2 voltage from phase W in volts
        ("temperature_2", ctypes.c_float),  # motor 2 estimated temperature in K
        ("encoder_pivot", ctypes.c_float),  # encoder pivot value in rad (wrapping at -PI and +PI)
        ("velocity_pivot", ctypes.c_float),  # encoder pivot velocity in rad/s
        ("voltage_bus", ctypes.c_float),  # bus voltage in volts
        ("imu_ts", ctypes.c_uint64),  # EtherCAT timestamp (ns) of IMU sensor acquisition
        ("accel_x", ctypes.c_float),  # IMU accelerometer X-axis in m/s2
        ("accel_y", ctypes.c_float),  # IMU accelerometer Y-axis in m/s2
        ("accel_z", ctypes.c_float),  # IMU accelerometer Z-axis in m/s2
        ("gyro_x", ctypes.c_float),  # IMU gyro X-axis in rad/s
        ("gyro_y", ctypes.c_float),  # IMU gyro Y-axis in rad/s
        ("gyro_z", ctypes.c_float),  # IMU gyro Z-axis in rad/s
        ("temperature_imu", ctypes.c_float),  # IMU temperature in K
        ("pressure", ctypes.c_float),  # barometric pressure in Pa absolute
        ("current_in", ctypes.c_float),  # current input
    ]


# From https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/include/kelo_tulip/soem/ethercattype.h#L157
EC_STATE_SAFE_OP = 0x04
EC_STATE_OPERATIONAL = 0x08

COM1_ENABLE1 = 0x0001
COM1_ENABLE2 = 0x0002
COM1_MODE_TORQUE = 0x0 << 2
COM1_MODE_DTORQUE = 0x1 << 2
COM1_MODE_VELOCITY = 0x2 << 2
COM1_MODE_DVELOCITY = 0x3 << 2
COM1_EMERGENCY1 = 0x0010
COM1_EMERGENCY2 = 0x0020
COM1_ENABLESERVO = 0x0400
COM1_SERVOCLOSE = 0x0800
COM1_USE_TS = 0x8000
