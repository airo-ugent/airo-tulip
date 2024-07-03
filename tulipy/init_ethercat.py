import time

import pysoem
import yaml

import ctypes

COM1_ENABLE1 = 0x0001
COM1_ENABLE2 = 0x0002
COM1_MODE_VELOCITY = (0x2 << 2)

from velocity_platform_controller import VelocityPlatformController


class RxPDO1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('command1', ctypes.c_uint16),  # Command bits as defined in COM1_
        ('command2', ctypes.c_uint16),  # Command bits as defined in COM2_
        ('setpoint1', ctypes.c_float),  # Setpoint 1
        ('setpoint2', ctypes.c_float),  # Setpoint 2
        ('limit1_p', ctypes.c_float),  # Upper limit 1
        ('limit1_n', ctypes.c_float),  # Lower limit 1
        ('limit2_p', ctypes.c_float),  # Upper limit 2
        ('limit2_n', ctypes.c_float),  # Lower limit 2
        ('timestamp', ctypes.c_uint64)  # EtherCAT timestamp (ns) setpoint execution

    ]


ECAT_DEVICE = "eno1"
EC_STATE_SAFE_OP = 0x04
EC_STATE_OPERATIONAL = 0x08

with open("example.yaml") as f:
    config = yaml.load(f, yaml.CLoader)

num_wheels = config['num_wheels']
wheel_configs = [config[f'wheel{i}'] for i in range(num_wheels)]


def main():
    master = pysoem.Master()

    master.open(ECAT_DEVICE)

    wkc = master.config_init()
    if wkc == 0:
        print("No EtherCAT slaves were found.")
        master.close()
        return

    master.config_map()
    print(f"Found {len(master.slaves)} slaves")
    for slave in master.slaves:
        print(slave.id, slave.man, slave.name)

    for i in range(num_wheels):
        slave_ethercat_number = wheel_configs[i]['ethercat_number']  # TODO wheel_config class
        print(f"Wheel #{i} is EtherCAT slave {slave_ethercat_number}.")

        if slave_ethercat_number > len(master.slaves):  # Start index is 1.
            print(
                f"Found only {len(master.slaves)} EtherCAT slaves, but config requires at least {slave_ethercat_number}.")
            return

    master.read_state()
    requested_state = EC_STATE_SAFE_OP
    found_state = master.state_check(requested_state)
    if found_state != requested_state:
        print("Not all EtherCAT slaves reached a safe operational state.")
        # TODO: check and report which slave was the culprit.
        return False

    print('safe operation state reached')
    #
    # data = RxPDO1()
    # data.timestamp = 1
    # data.command1 = 0
    # data.limit1_p = 0
    # data.limit1_n = 0
    # data.limit2_p = 0
    # data.limit2_n = 0
    # data.setpoint1 = 0
    # data.setpoint2 = 0
    # for i in range(num_wheels):
    #     master.slaves[wheel_configs[i]['ethercat_number']].outputs = b'\x00' * 40#bytes(data)

    # master.send_processdata()

    print("Requesting operational state for all EtherCAT slaves.")
    master.state = EC_STATE_OPERATIONAL
    master.send_processdata()
    master.receive_processdata()
    master.write_state()

    # Check if all slaves are actually operational.
    requested_state = EC_STATE_OPERATIONAL
    found_state = master.state_check(requested_state)
    print('master', master.state)
    if found_state == requested_state:
        print("All EtherCAT slaves reached a safe operational state.")
    else:
        print("Not all EtherCAT slaves reached a safe operational state.")
        return False

    for slave in master.slaves:
        print(f"name {slave.name} Obits {len(slave.output)} Ibits {len(slave.input)} state {slave.state}")

    # for (int cnt = 1; cnt <= ecx_slavecount; cnt++) {
    # 		std::cout << "Slave: " << cnt  << " Name: " << ecx_slave[cnt].name  << " Output size: " << ecx_slave[cnt].Obits
    # 			<< "bits Input size: " << ecx_slave[cnt].Ibits << "bits State: " << ecx_slave[cnt].state
    # 			<< " delay: " << ecx_slave[cnt].pdelay << std::endl; //<< " has dclock: " << (bool)ecx_slave[cnt].hasdc;
    # 	}

    # AT THIS POINT READY

    data = RxPDO1()
    data.timestamp = 100 * 1000  # TODO
    data.command1 = COM1_ENABLE1 | COM1_ENABLE2 | COM1_MODE_VELOCITY
    data.limit1_p = 20
    data.limit1_n = -20
    data.limit2_p = 20
    data.limit2_n = -20
    data.setpoint1 = 0
    data.setpoint2 = 0

    while True:
        for i in range(num_wheels):
            print(master.slaves[wheel_configs[i]['ethercat_number'] - 1].name)
            print(len(master.slaves[wheel_configs[i]['ethercat_number'] - 1].output), len(bytes(data)))
            master.slaves[wheel_configs[i]['ethercat_number'] - 1].output = bytes(data)
        wkc = master.send_processdata()
        print(wkc)

    # velocity_platform_controller = VelocityPlatformController()
    # velocity_platform_controller.initialise(wheel_configs)
    # # Initialize time and state of VPC
    # # TODO: put this in set_platform_velocity_target instead for safety
    # velocity_platform_controller.calculate_platform_ramped_velocities()
    # velocity_platform_controller.set_platform_velocity_target(.0,.0,.0)
    # # for each wheel
    # velocity_platform_controller.calculate_platform_ramped_velocities()
    # setpoint_l, setpoint_r = velocity_platform_controller.calculate_wheel_target_velocity()
    # # TODO invert?

    time.sleep(2)

    master.close()


if __name__ == '__main__':
    main()
