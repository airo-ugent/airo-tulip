"""Rerun monitor logger for logging all values to rerun.

Note: This currently causes a memory leak, and it is recommended to not use this until
https://github.com/airo-ugent/airo-tulip/issues/25 is resolved."""

import numpy as np
import rerun as rr
from airo_tulip.hardware.platform_monitor import PlatformMonitor


class RerunMonitorLogger:
    def __init__(self, *, rerun_application_id: str = "kelo", rerun_max_memory_gb: int = 1):
        """Initialize the Rerun monitor logger.

        Args:
            rerun_application_id: Application ID for rerun.
            rerun_max_memory_gb: Maximum amount of memory rerun is allowed to consume."""
        rr.init(rerun_application_id, spawn=False)
        rr.serve(open_browser=False, server_memory_limit=f"{rerun_max_memory_gb}GB")

    def step(self, monitor: PlatformMonitor):
        """Log all values to rerun."""
        for drive_index in range(monitor.num_wheels):
            status1 = monitor.get_status1(drive_index)
            status2 = monitor.get_status2(drive_index)
            encoder_wheel1, encoder_wheel2, encoder_pivot = monitor.get_encoder(drive_index)
            velocity_x, velocity_y, velocity_a = monitor.get_velocity(drive_index)
            current_d_wheel1, current_d_wheel2 = monitor.get_current(drive_index)
            voltage_wheel1, voltage_wheel2 = monitor.get_voltage(drive_index)
            temperature_wheel1, temperature_wheel2, temperature_imu = monitor.get_temperature(drive_index)
            voltage_bus = monitor.get_voltage_bus(drive_index)
            acceleration_x, acceleration_y, acceleration_z = monitor.get_acceleration(drive_index)
            gyro_x, gyro_y, gyro_z = monitor.get_gyro(drive_index)
            pressure = monitor.get_pressure(drive_index)
            current_in = monitor.get_current_in(drive_index)
            power = monitor.get_power(drive_index)
            odometry = monitor.get_estimated_robot_pose()

            rr.log(f"drive_{drive_index}/status1", rr.Scalar(status1))
            rr.log(f"drive_{drive_index}/status2", rr.Scalar(status2))
            rr.log(f"drive_{drive_index}/encoder/wheel1", rr.Scalar(encoder_wheel1))
            rr.log(f"drive_{drive_index}/encoder/wheel2", rr.Scalar(encoder_wheel2))
            rr.log(f"drive_{drive_index}/encoder/pivot", rr.Scalar(encoder_pivot))
            rr.log(f"drive_{drive_index}/velocity_x", rr.Scalar(velocity_x))
            rr.log(f"drive_{drive_index}/velocity_y", rr.Scalar(velocity_y))
            rr.log(f"drive_{drive_index}/velocity_a", rr.Scalar(velocity_a))
            rr.log(f"drive_{drive_index}/current_d/wheel1", rr.Scalar(current_d_wheel1))
            rr.log(f"drive_{drive_index}/current_d/wheel2", rr.Scalar(current_d_wheel2))
            rr.log(f"drive_{drive_index}/voltage/wheel1", rr.Scalar(voltage_wheel1))
            rr.log(f"drive_{drive_index}/voltage/wheel2", rr.Scalar(voltage_wheel2))
            rr.log(f"drive_{drive_index}/temperature/wheel1", rr.Scalar(temperature_wheel1))
            rr.log(f"drive_{drive_index}/temperature/wheel2", rr.Scalar(temperature_wheel2))
            rr.log(f"drive_{drive_index}/temperature/imu", rr.Scalar(temperature_imu))
            rr.log(f"drive_{drive_index}/voltage_bus", rr.Scalar(voltage_bus))
            rr.log(f"drive_{drive_index}/acceleration/x", rr.Scalar(acceleration_x))
            rr.log(f"drive_{drive_index}/acceleration/y", rr.Scalar(acceleration_y))
            rr.log(f"drive_{drive_index}/acceleration/z", rr.Scalar(acceleration_z))
            rr.log(f"drive_{drive_index}/gyro/x", rr.Scalar(gyro_x))
            rr.log(f"drive_{drive_index}/gyro/y", rr.Scalar(gyro_y))
            rr.log(f"drive_{drive_index}/gyro/z", rr.Scalar(gyro_z))
            rr.log(f"drive_{drive_index}/pressure", rr.Scalar(pressure))
            rr.log(f"drive_{drive_index}/current_in", rr.Scalar(current_in))
            rr.log(f"drive_{drive_index}/power", rr.Scalar(power))

            rr.log(f"platform/odometry/position", rr.Points2D([odometry[0], odometry[1]]))
            rr.log(
                f"platform/odometry/direction",
                rr.Arrows2D(
                    origins=[odometry[0], odometry[1]], vectors=[0.1 * np.cos(odometry[2]), 0.1 * np.sin(odometry[2])]
                ),
            )
