import pysoem
from typing import List

from tulipy.ethercat import *

class PlatformMonitor:

    def __init__(self, master: pysoem.Master, wheel_configs: List[WheelConfig]):
        self._master = master
        self._wheel_configs = wheel_configs
        self._num_wheels = len(wheel_configs)

        self._status1: List[int]
        self._status2: List[int]
        self._encoder: List[List[float]]
        self._velocity: List[List[float]]
        self._current: List[List[float]]
        self._voltage: List[List[float]]
        self._temperature: List[List[float]]
        self._voltage_bus: List[float]
        self._accel: List[List[float]]
        self._gyro: List[List[float]]
        self._pressure: List[float]
        self._current_in: List[float]

    def step(self) -> None:
        process_data = [self._get_process_data(i) for i in range(self._num_wheels)]
        self._status1 = [pd.status1 for pd in process_data]
        self._status2 = [pd.status2 for pd in process_data]
        self._encoder = [[pd.encoder_1, pd.encoder_2, pd.encoder_pivot] for pd in process_data]
        self._velocity = [[pd.velocity_1, pd.velocity_2, pd.velocity_pivot] for pd in process_data]
        self._current = [[pd.current_1_d, pd.current_2_d] for pd in process_data]
        self._voltage = [[pd.voltage_1, pd.voltage_2] for pd in process_data]
        self._temperature = [[pd.temperature_1, pd.temperature_2, pd.temperature_imu] for pd in process_data]
        self._voltage_bus = [pd.voltage_bus for pd in process_data]
        self._accel = [[pd.accel_x, pd.accel_y, pd.accel_z] for pd in process_data]
        self._gyro = [[pd.gyro_x, pd.gyro_y, pd.gyro_z] for pd in process_data]
        self._pressure = [pd.pressure for pd in process_data]
        self._current_in = [pd.current_in for pd in process_data]

    def get_status1(self, wheel_index: int) -> int:
        return self._status1[wheel_index]

    def get_status2(self, wheel_index: int) -> int:
        return self._status2[wheel_index]

    def get_encoder(self, wheel_index: int) -> List[float]:
        return self._encoder[wheel_index]

    def get_velocity(self, wheel_index: int) -> List[float]:
        return self._velocity[wheel_index]

    def get_current(self, wheel_index: int) -> List[float]:
        return self._current[wheel_index]

    def get_voltage(self, wheel_index: int) -> List[float]:
        return self._voltage[wheel_index]

    def get_temperature(self, wheel_index: int) -> List[float]:
        return self._temperature[wheel_index]

    def get_voltage_bus(self, wheel_index: int) -> float:
        return self._voltage_bus[wheel_index]

    def get_voltage_bus_max(self) -> float:
        return max(self._voltage_bus)

    def get_acceleration(self, wheel_index: int) -> List[float]:
        return self._accel[wheel_index]

    def get_gyro(self, wheel_index: int) -> List[float]:
        return self._gyro[wheel_index]

    def get_pressure(self, wheel_index: int) -> float:
        return self._pressure[wheel_index]

    def get_current_in(self, wheel_index: int) -> float:
        return self._current_in[wheel_index]

    def get_current_in_total(self) -> float:
        return sum(self._current_in)

    def get_power(self, wheel_index: int) -> float:
        return self._voltage_bus[wheel_index] * self._current_in[wheel_index]

    def get_power_total(self) -> float:
        return sum([self._voltage_bus[i] * self._current_in[i] for i in range(self._num_wheels)])

    def _get_process_data(self, wheel_index: int) -> TxPDO1:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        return TxPDO1.from_buffer_copy(self._master.slaves[ethercat_index-1].input)

    def _set_process_data(self, wheel_index: int, data: RxPDO1) -> None:
        ethercat_index = self._wheel_configs[wheel_index].ethercat_number
        self._master.slaves[ethercat_index-1].output = bytes(data)
