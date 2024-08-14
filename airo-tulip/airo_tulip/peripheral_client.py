import time

import serial


class PeripheralClient:
    def __init__(self, port, baud_rate):
        # Connect to the peripheral server
        self._ser = serial.Serial(port, baud_rate, timeout=1)
        time.sleep(2)
        assert self.ping(), "Could not establish connection to peripheral server"

    def _transceive(self, command):
        # Send command to server
        self._ser.write((command + "\n").encode("utf-8"))

        # Read response from server
        while True:
            if self._ser.in_waiting > 0:
                response = self._ser.readline().decode("utf-8").strip()
                if response:
                    return response

    def ping(self):
        res = self._transceive("PING")
        return res == "PONG"

    def get_flow(self):
        res = self._transceive("FLOW")
        tokens = res.split(",")
        x = int(tokens[0])
        y = int(tokens[1])
        return x, y
