"""Stop the UR robot arm remotely, without needing to connect a monitor and peripherals to the control box."""
import argparse
import socket
import sys


class Dashboard:
    def __init__(self, ip):
        self.ip = ip
        self.port = 29999
        self.timeout = 5
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.ip, self.port))
        # Receive initial "Connected" Header
        reply = self.sock.recv(1096)
        return reply != b''

    def send_and_receive(self, command):
        try:
            self.sock.sendall((command + '\n').encode())
            return self.get_reply()
        except (ConnectionResetError, ConnectionAbortedError):
            print('The connection was lost to the robot. Please connect and try running again.')
            self.close()
            sys.exit()

    def get_reply(self):
        """
        read one line from the socket
        :return: text until new line
        """
        collected = b''
        while True:
            part = self.sock.recv(1)
            if part != b"\n":
                collected += part
            elif part == b"\n":
                break
        return collected.decode("utf-8")

    def close(self):
        self.sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, help="IP address of the UR control box", default="localhost")

    args = parser.parse_args()

    print("Setting up connection...")
    dash = Dashboard(args.ip)
    if dash.connect():
        print("Connected.")
    else:
        print("Failed to connect.")
        exit(1)
    # Check to see if robot is in remote mode.
    remote_check = dash.send_and_receive('is in remote control')
    if 'false' in remote_check:
        print(
            "Robot is in local mode. Some commands may not function.\nYou will need to reboot the robot or manually enabled remote control.")
        exit(1)
    else:
        print("Robot is in remote mode. Will continue")

    print("Engaging brakes.")
    dash.send_and_receive("brake engage")

    print("Powering off.")
    dash.send_and_receive("power off")

    dash.close()