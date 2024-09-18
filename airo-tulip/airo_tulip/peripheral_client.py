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
        x1 = int(tokens[0])
        y1 = int(tokens[1])
        x2 = int(tokens[2])
        y2 = int(tokens[3])
        return x1, y1, x2, y2

    def set_leds_idle(self):
        res = self._transceive("LED IDLE")
        return res == "OK"

    def set_leds_active(self, angle, velocity):
        angle = angle % (2 * 3.1415)
        res = self._transceive(f"LED ACTIVE {angle} {velocity}")
        return res == "OK"

    def set_leds_error(self):
        res = self._transceive("LED ERROR")
        return res == "OK"
