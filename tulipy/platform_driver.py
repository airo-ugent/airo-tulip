from dataclasses import dataclass
from typing import List

import pysoem
from loguru import logger

from tulipy.ethercat import EC_STATE_SAFE_OP, EC_STATE_OPERATIONAL
from tulipy.kelo_drive_api import RxPDO1


# todo: https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/src/modules/RobileMasterBattery.cpp
class EtherCATModule:
    def init_ethercat(self, slaves) -> bool:
        pass

    def step(self):
        pass


@dataclass
class WheelConfig:
    ethercat_number: int
    x: float
    y: float
    a: float
    critical: bool
    enable: bool
    reverse_velocity: bool


@dataclass
class WheelData:
    enable: bool
    error: bool
    error_timestamp: bool


class TulipPlatformDriver:
    # Constants taken directly from KELO: https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/src/PlatformDriver.cpp
    WHEEL_DISTANCE = 0.0775
    WHEEL_DIAMETER = 0.104
    CURRENT_STOP = 1
    CURRENT_DRIVE = 20
    MAX_V_LIN = 1.5
    MAX_V_A = 1.0
    MAX_V_LIN_ACC = 0.0025  # Per millisecond, same value for deceleration
    MAX_ANGLE_ACC = 0.01  # At vlin=0, per msec, same value for deceleration
    MAX_V_A_ACC = 0.01  # Per millisecond, same value for deceleration
    WHEEL_SET_POINT_MIN = 0.01
    WHEEL_SET_POINT_MAX = 35.0

    def __init__(self, device: str, ecat_modules: List[EtherCATModule], wheel_configs: List[WheelConfig],
                 wheel_data: List[WheelData], first_wheel: int, num_wheels: int):
        self.device = device
        self.ecat_modules = ecat_modules
        self.wheel_configs = wheel_configs
        self.wheel_data = wheel_data
        self.first_wheel = first_wheel
        self.num_wheels = num_wheels

        assert len(wheel_configs) == len(wheel_data) == num_wheels

        # TODO: VelocityPlatformController::initialize?

        self.master = pysoem.Master()

        self.process_data_wheels = [RxPDO1()] * self.num_wheels
        self.last_process_data = None

    def initialise_ethercat(self) -> bool:
        self.master.open(self.device)

        wkc = self.master.config_init()
        if wkc == 0:
            logger.error("No EtherCAT slaves were found.")
            return False

        self.master.config_map()

        logger.debug(f"Found {len(self.master.slaves)} slaves.")
        for i in range(len(self.master.slaves)):
            logger.debug(f"EtherCAT slave {i + 1} has ID {id}.")

        for i in range(self.num_wheels):
            slave_ethercat_number = self.wheel_configs[i].ethercat_number  # TODO wheel_config class
            logger.debug(f"Wheel #{i} is EtherCAT slave {slave_ethercat_number}.")

            if slave_ethercat_number > len(self.master.slaves):  # Start index is 1.
                logger.error(
                    f"Found only {len(self.master.slaves)} EtherCAT slaves, but config requires at least {slave_ethercat_number}.")
                return False

        for ecat_module in self.ecat_modules:
            ok = ecat_module.init_ethercat()  # TODO args?
            if not ok:
                logger.error("Failed to initialize EtherCAT module.")
                return False

        logger.debug(f"{len(self.master.slaves)} EtherCAT slaves found and configured.")

        self.master.read_state()
        requested_state = EC_STATE_SAFE_OP
        found_state = self.master.state_check(requested_state)
        if found_state != requested_state:
            logger.error("Not all EtherCAT slaves reached a safe operational state.")
            # TODO: check and report which slave was the culprit.
            return False

        # Set command to zero, specifically for SmartWheel.
        data = RxPDO1()
        data.timestamp = 1
        data.command1 = 0
        data.limit1_p = 0
        data.limit1_n = 0
        data.limit2_p = 0
        data.limit2_n = 0
        data.setpoint1 = 0
        data.setpoint2 = 0
        for i in range(self.num_wheels):
            self.master.slaves[self.wheel_configs[i].ethercat_number].output = bytes(data)

        self.master.send_processdata()

        logger.debug("Requesting operational state for all EtherCAT slaves.")
        self.master.slaves[0].state = EC_STATE_OPERATIONAL
        self.master.send_processdata()
        self.master.receive_processdata()
        self.master.write_state()

        requested_state = EC_STATE_OPERATIONAL
        found_state = self.master.state_check(requested_state)
        if found_state == requested_state:
            logger.debug("All EtherCAT slaves reached a safe operational state.")
        else:
            logger.error("Not all EtherCAT slaves reached a safe operational state.")
            return False

        for i in range(self.num_wheels):
            self.process_data_wheels[i] = self._get_process_data(self.wheel_configs[i].ethercat_number)
        self.last_process_data = self.process_data_wheels

        # TODO: start ethercat thread.

        return True

    def _get_process_data(self, slave: int) -> RxPDO1:
        return RxPDO1.from_buffer(self.master.slaves[slave].inputs)
