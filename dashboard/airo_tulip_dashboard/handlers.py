import subprocess

from loguru import logger


def handle_message(data: bytes) -> bytes:
    if data == b'shutdown':
        shutdown()

        return b'shutting down'
    elif data == b'ur start':
        logger.info("Starting UR robot...")
        result = subprocess.run(["start_ur"])
        return process_result(result)
    elif data == b'ur stop':
        logger.info("Stopping UR robot...")
        result = subprocess.run(["stop_ur"])
        return process_result(result)
    elif data == b'tulip start':
        logger.info("Starting tulip server...")
        result = subprocess.run(["start_tulip"])
        return process_result(result)
    elif data == b'tulip stop':
        logger.info("Stopping tulip server...")
        result = subprocess.run(["stop_tulip"])
        return process_result(result)
    else:
        logger.error(f"Unknown command received: {data}")
        return b'error'


def shutdown():
    logger.info("Received shutdown command. Shutting down...")
    logger.info("Shutting down UR robot...")
    subprocess.run(["stop_ur"])
    logger.info("Shutting down KELO CPU in 60 seconds...")
    subprocess.run(["shutdown"])


def process_result(result: subprocess.CompletedProcess) -> bytes:
    if result.returncode == 0:
        return b'success'
    else:
        return b'error'
