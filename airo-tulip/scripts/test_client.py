import time

import zmq
from loguru import logger

from airo_tulip.server.messages import SetPlatformVelocityTargetMessage, StopServerMessage, HeartbeatMessage


class SimpleClient:
    def __init__(self, robot_ip: str, robot_port: int):
        address = f"tcp://{robot_ip}:{robot_port}"
        logger.info(f"Connecting to {address}...")
        self._zmq_ctx = zmq.Context()
        self._zmq_socket = self._zmq_ctx.socket(zmq.REQ)
        self._zmq_socket.connect(address)
        logger.info(f"Connected to {address}.")

    def send_test_request(self):
        msg = SetPlatformVelocityTargetMessage(0.0, 0.0, 0.0)
        self._zmq_socket.send_pyobj(msg)
        response = self._zmq_socket.recv_pyobj()
        print(response)


def test():
    import math
    client = SimpleClient("localhost", 49789)
    msg = SetPlatformVelocityTargetMessage(0.0, 0.0, math.pi/8)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(2)

    msg = SetPlatformVelocityTargetMessage(0.2, 0.0, 0.0)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(1)

    msg = SetPlatformVelocityTargetMessage(0.0, 0.2, 0.0)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(1)

    msg = SetPlatformVelocityTargetMessage(-0.2, 0.0, 0.0)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(1)

    msg = SetPlatformVelocityTargetMessage(0.0, -0.2, 0.0)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(1)

    msg = SetPlatformVelocityTargetMessage(0.0, 0.0, -math.pi/8)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(2)

    msg = SetPlatformVelocityTargetMessage(0.0, 0.0, 0.0)
    client._zmq_socket.send_pyobj(msg)
    response =client._zmq_socket.recv_pyobj()
    time.sleep(0.5)

    client._zmq_socket.send_pyobj(StopServerMessage())
    _response = client._zmq_socket.recv_pyobj()


if __name__ == "__main__":
    test()
