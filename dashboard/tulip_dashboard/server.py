import socket
import threading

from loguru import logger

from dashboard.tulip_dashboard.handlers import handle_message


def handle_client(conn: socket, addr: str):
    while True:
        data = conn.recv(1024)
        if not data:
            break
        logger.info(f"Received data from {addr}: {data}, {len(data)}")
        handle_message(data)
    conn.close()
    logger.info(f"Remote client {addr} closed the connection.")


def start_server(host: str = '0.0.0.0', port: int = 49790):
    # TODO: start a separate thread that monitors the battery status of the KELO and shuts down if unsafe levels are reached.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        logger.info(f"Listening on port {port}...")
        while True:
            conn, addr = s.accept()
            logger.info(f"Accepting incoming connection from {addr}...")
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()


if __name__ == '__main__':
    start_server()
