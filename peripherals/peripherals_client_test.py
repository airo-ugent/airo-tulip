import time

import serial

# Configure the serial port and baud rate
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200


def transceive(ser, command):
    # Send command to server
    ser.write((command + "\n").encode("utf-8"))

    # Read response from server
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode("utf-8").strip()
            if response:
                return response


def main():
    # Create a serial connection
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)  # Wait for the connection to establish

        res = transceive(ser, "PING")
        print(res)

        res = transceive(ser, "LED BOOT")
        print(res)

        time.sleep(1)

        res = transceive(ser, "BNO")
        print(res)

        time.sleep(0.1)
        res = transceive(ser, "FLOW")
        print(res)

        res = transceive(ser, "LED DISCO")
        print(res)


if __name__ == "__main__":
    main()
