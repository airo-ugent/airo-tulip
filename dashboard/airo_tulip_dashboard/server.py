import socket
import subprocess
import threading

from airo_tulip_dashboard.handlers import handle_message, shutdown
from loguru import logger


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
