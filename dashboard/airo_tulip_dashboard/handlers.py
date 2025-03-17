import os
import signal
import subprocess

from loguru import logger


def handle_message(data: bytes) -> bytes:
    if data == b"shutdown":
        shutdown()

        return b"shutting down"
    elif data == b"ur start":
        logger.info("Starting UR robot...")
        result = subprocess.run(["start_ur"])
        return process_result(result)
    elif data == b"ur stop":
        logger.info("Stopping UR robot...")
        result = subprocess.run(["stop_ur"])
        return process_result(result)
    elif data == b"tulip start":
        logger.info("Starting tulip server...")
        process = subprocess.Popen(["start_tulip"], shell=True)
        return bytes(process.pid)
    elif data.startswith(b"tulip stop"):
        pid = int(data.split(b" ")[-1])
        logger.info("Stopping tulip server...")
        os.kill(pid, signal.SIGTERM)
        return b"success"
    elif data == b"kill":
        logger.info('Killing dashboard server... You can restart it with: sudo -E env "PATH=$PATH" start_dashboard')
        return b"kill"
    else:
        logger.error(f"Unknown command received: {data}")
        return b"error"


def shutdown():
    logger.info("Received shutdown command. Shutting down...")
    logger.info("Shutting down UR robot...")
    subprocess.run(["stop_ur"])
    logger.info("Shutting down KELO CPU in 60 seconds...")
    subprocess.run(["shutdown"])


def process_result(result: subprocess.CompletedProcess) -> bytes:
    if result.returncode == 0:
        return b"success"
    else:
        return b"error"
