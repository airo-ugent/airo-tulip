import socket
import subprocess
import threading
import time
from typing import Final

from airo_tulip_dashboard.handlers import handle_message, shutdown
from cyclonedds.sub import DataReader
from loguru import logger

MIN_ALLOWED_VOLTAGE_BUS: Final[float] = 26.0


def handle_client(conn: socket, addr: str, should_stop_running: threading.Event):
    while not should_stop_running.is_set():
        logger.info(f"Waiting for data from {addr}...")
        data = conn.recv(1024)
        logger.info(f"Received data from {addr}: {data}")
        if not data:
            break
        logger.info(f"Received non-empty data from {addr}: {data}, {len(data)}")
        response = handle_message(data)
        conn.sendall(response)
    if should_stop_running.is_set():
        logger.info(f"Shutting down connection to {addr} due to low battery voltage.")
        shutdown()
    else:
        logger.info(f"Remote client {addr} closed the connection.")
    conn.close()


def monitor_battery(reader: DataReader, frequency: int, should_stop_running: threading.Event):
    while not should_stop_running.is_set():
        start_time = time.time()

        messages = reader.take()
        for message in messages:
            voltage = message.voltage_bus
            if voltage < MIN_ALLOWED_VOLTAGE_BUS:
                logger.warning(f"Low battery voltage: {voltage} V. Will shut down KELO.")
                should_stop_running.set()

        end_time = time.time()
        # Sleep for remainder of the period.
        sleep_time = 1 / frequency - (end_time - start_time)
        if sleep_time > 0:
            time.sleep(sleep_time)


def enable_UR_connection():
    logger.info("Enabling UR connection...")
    subprocess.run(["nmcli", "connection", "up", "UR"])


def start_server(host: str = '0.0.0.0', port: int = 49790):
    enable_UR_connection()

    should_stop_running = threading.Event()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        logger.info(f"Listening on port {port}...")
        while not should_stop_running.is_set():
            conn, addr = s.accept()
            logger.info(f"Accepting incoming connection from {addr}...")
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, should_stop_running))
            client_thread.start()


if __name__ == '__main__':
    start_server()
