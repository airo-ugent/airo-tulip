"""The RobilePlatform drives the robot through EtherCAT."""

from typing import List

import pysoem
from airo_tulip.hardware.ethercat import EC_STATE_OPERATIONAL, EC_STATE_SAFE_OP
from airo_tulip.hardware.logging.monitor_rerun import RerunMonitorLogger
from airo_tulip.hardware.peripheral_client import PeripheralClient, StatusLed
from airo_tulip.hardware.platform_driver import PlatformDriver, PlatformDriverType
from airo_tulip.hardware.platform_monitor import PlatformMonitor
from airo_tulip.hardware.structs import WheelConfig
from loguru import logger


class RobilePlatform:
    """The RobilePlatform drives the robot through EtherCAT."""

    def __init__(
        self,
        device: str,
        wheel_configs: List[WheelConfig],
        controller_type: PlatformDriverType,
        enable_rerun: bool = False,
    ):
        """Initialize the RobilePlatform.

        Args:
            device: The EtherCAT device name.
            wheel_configs: A list of wheel configurations specific to your platform.
            enable_rerun: Enable logging of monitor values to Rerun. Disabled by default."""
        self._device = device
        self._ethercat_initialized = False

        self._master = pysoem.Master()
        try:
            self._peripheral_client = PeripheralClient("/dev/ttyACM0", 115200)
        except Exception as e:
            logger.error(f"Could not connect to the peripheral client. Cause:\n{e}")
            self._peripheral_client = None
        self._driver = PlatformDriver(self._master, wheel_configs, controller_type, self._peripheral_client)
        self._monitor = PlatformMonitor(self._master, wheel_configs, self._peripheral_client)

        self._enable_rerun = enable_rerun
        if self._enable_rerun:
            self._rerun_monitor_logger = RerunMonitorLogger()

        if self._peripheral_client is not None:
            self._peripheral_client.set_status_led(StatusLed.POWER, True)

    @property
    def driver(self) -> PlatformDriver:
        return self._driver

    @property
    def monitor(self) -> PlatformMonitor:
        return self._monitor

    def init_ethercat(self) -> bool:
        """
        Initializes the EtherCAT interface and all connected slaves into an operational state.
        Returns `True` if initialisation is successful, `False` otherwise.
        """
        # Open EtherCAT device if not already done so
        if not self._ethercat_initialized:
            self._master.open(self._device)
            self._ethercat_initialized = True

            if self._peripheral_client is not None:
                self._peripheral_client.set_status_led(StatusLed.WHEELS_ENABLED, True)

        # Configure slaves
        wkc = self._master.config_init()
        if wkc == 0:
            logger.warning("No EtherCAT slaves were found.")
            self._master.close()
            return False

        self._master.config_map()
        logger.info(f"Found {len(self._master.slaves)} slaves")
        for slave in self._master.slaves:
            logger.info(f"{slave.id} {slave.man} {slave.name}")

        # Check if all slaves reached SAFE_OP state
        self._master.read_state()
        requested_state = EC_STATE_SAFE_OP
        found_state = self._master.state_check(requested_state)
        if found_state != requested_state:
            logger.warning("Not all EtherCAT slaves reached a safe operational state.")

            if self._peripheral_client is not None:
                self._peripheral_client.set_status_led(StatusLed.WHEELS_ENABLED, False)
                self._peripheral_client.set_status_led(StatusLed.WARNING, False)

            # TODO: check and report which slave was the culprit.
            return False

        # Request OP state for all slaves
        logger.info("Requesting operational state for all EtherCAT slaves.")
        self._master.state = EC_STATE_OPERATIONAL
        self._master.send_processdata()
        self._master.receive_processdata()
        self._master.write_state()

        # Check if all slaves are actually operational.
        requested_state = EC_STATE_OPERATIONAL
        found_state = self._master.state_check(requested_state)
        if found_state == requested_state:
            logger.info("All EtherCAT slaves reached a safe operational state.")
        else:
            logger.warning("Not all EtherCAT slaves reached a safe operational state.")
            if self._peripheral_client is not None:
                self._peripheral_client.set_status_led(StatusLed.WHEELS_ENABLED, False)
                self._peripheral_client.set_status_led(StatusLed.WARNING, False)
            return False

        for slave in self._master.slaves:
            logger.debug(f"name {slave.name} Obits {len(slave.output)} Ibits {len(slave.input)} state {slave.state}")

        if self._peripheral_client is not None:
            self._peripheral_client.set_status_led(StatusLed.WHEELS_ENABLED, True)
            self._peripheral_client.set_status_led(StatusLed.WARNING, True)

        return True

    def step(self):
        """
        Main processing loop of the EtherCAT master, must be called frequently.
        """
        self._master.receive_processdata()
        self._monitor.step()
        if self._enable_rerun:
            self._rerun_monitor_logger.step(self._monitor)
        self._set_battery_status_led()
        self._driver.step()
        self._master.send_processdata()

    def _set_battery_status_led(self):
        voltage_bus_max = self._monitor.get_voltage_bus_max()
        if self._peripheral_client is not None:
            self._peripheral_client.set_status_led(StatusLed.BATTERY, voltage_bus_max >= 26)
