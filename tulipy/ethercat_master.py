import pysoem
from typing import List
from platform_driver import PlatformDriver

# From https://github.com/kelo-robotics/kelo_tulip/blob/1a8db0626b3d399b62b65b31c004e7b1831756d7/include/kelo_tulip/soem/ethercattype.h#L157
EC_STATE_SAFE_OP = 0x04
EC_STATE_OPERATIONAL = 0x08

class EtherCATMaster():
    def __init__(self, device: str, driver: PlatformDriver):
        self._device = device
        self._driver = driver
        self._ethercat_initialized = False
        self._master = pysoem.Master()

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
        print(f"Found {len(master.slaves)} slaves")
        for slave in self._master.slaves:
            print(slave.id, slave.man, slave.name)

        # Initialize driver
        ok = self._driver.init()
        if not ok:
            print("Cannot initialize PlatformDriver.")
            return False

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
        self._driver.step()
        self._master.send_processdata()

    
