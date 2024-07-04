import pysoem
from typing import List

from airo_tulip.structs import WheelConfig
from airo_tulip.platform_driver import PlatformDriver
from airo_tulip.platform_monitor import PlatformMonitor
from airo_tulip.ethercat import EC_STATE_SAFE_OP, EC_STATE_OPERATIONAL

class RobilePlatform():
    def __init__(self, device: str, wheel_configs: List[WheelConfig]):
        self._device = device
        self._ethercat_initialized = False

        self._master = pysoem.Master()
        self._driver = PlatformDriver(self._master, wheel_configs)
        self._monitor = PlatformMonitor(self._master, wheel_configs)

    def get_driver(self) -> PlatformDriver:
        return self._driver

    def get_monitor(self) -> PlatformMonitor:
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

        # Configure slaves
        wkc = self._master.config_init()
        if wkc == 0:
            print("No EtherCAT slaves were found.")
            self._master.close()
            return False

        self._master.config_map()
        print(f"Found {len(self._master.slaves)} slaves")
        for slave in self._master.slaves:
            print(slave.id, slave.man, slave.name)

        # Check if all slaves reached SAFE_OP state
        self._master.read_state()
        requested_state = EC_STATE_SAFE_OP
        found_state = self._master.state_check(requested_state)
        if found_state != requested_state:
            print("Not all EtherCAT slaves reached a safe operational state.")
            # TODO: check and report which slave was the culprit.
            return False
        
        # Request OP state for all slaves
        print("Requesting operational state for all EtherCAT slaves.")
        self._master.state = EC_STATE_OPERATIONAL
        self._master.send_processdata()
        self._master.receive_processdata()
        self._master.write_state()

        # Check if all slaves are actually operational.
        requested_state = EC_STATE_OPERATIONAL
        found_state = self._master.state_check(requested_state)
        if found_state == requested_state:
            print("All EtherCAT slaves reached a safe operational state.")
        else:
            print("Not all EtherCAT slaves reached a safe operational state.")
            return False

        for slave in self._master.slaves:
            print(f"name {slave.name} Obits {len(slave.output)} Ibits {len(slave.input)} state {slave.state}")

        return True

    def loop(self):
        """
        Main processing loop of the EtherCAT master, must be called frequently.
        """
        self._master.receive_processdata()
        self._monitor.step()
        self._driver.step()
        self._master.send_processdata()

    
