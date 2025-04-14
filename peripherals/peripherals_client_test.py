import time
import math
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

        #res = transceive(ser, "LED BOOT")
        #print(res)

        time.sleep(1)

        while True:
            res = transceive(ser, "BNO")
            print(res)

            #tokens = res.split(",")
            #mx = float(tokens[0])
            #my = float(tokens[1])
            #heading = (90 - math.atan2(my, mx) * 180 / math.pi) % 360
            #print(heading)

            time.sleep(0.1)

        #time.sleep(0.1)
        #res = transceive(ser, "FLOW")
        #print(res)

        #res = transceive(ser, "LED STATUS 0 1")
        #print(res)

        #res = transceive(ser, "LED STATUS 1 0")
        #print(res)

        #res = transceive(ser, "LED STATUS 2 1")
        #print(res)

        #res = transceive(ser, "LED STATUS 3 0")
        #print(res)

        #res = transceive(ser, "LED STATUS 4 1")
        #print(res)


if __name__ == "__main__":
    main()
