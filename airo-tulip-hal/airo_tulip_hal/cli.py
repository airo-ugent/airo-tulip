"""Console entry point for the airo-tulip server.

Reads a YAML robot configuration file (EtherCAT device + drive layout, and optional Zenoh/loop
settings) and runs the :class:`~airo_tulip_hal.server.TulipServer`. The configuration lives in a data
file rather than in code because it is specific to each physical platform.

Installed as the ``airo-tulip-server`` console script:

    airo-tulip-server --config /path/to/robot.yaml
"""

import argparse

import yaml
from airo_tulip_hal.hardware.structs import WheelConfig
from airo_tulip_hal.server import RobotConfiguration, TulipServer
from loguru import logger

# Optional server settings that may appear in the config and map directly to TulipServer kwargs.
_OPTIONAL_SERVER_KEYS = ("robot_id", "router_endpoint", "loop_frequency", "watchdog_timeout")


def load_config(path: str) -> dict:
    """Load and minimally validate the YAML robot configuration."""
    with open(path) as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Config file '{path}' must contain a top-level mapping.")
    return config


def build_wheel_configs(wheels) -> list:
    """Build WheelConfig objects from the 'wheels' list in the config."""
    if not wheels:
        raise ValueError("Config must define at least one wheel under 'wheels'.")
    wheel_configs = []
    for i, wheel in enumerate(wheels):
        try:
            wheel_configs.append(
                WheelConfig(
                    ethercat_number=wheel["ethercat_number"],
                    x=wheel["x"],
                    y=wheel["y"],
                    a=wheel["a"],
                )
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid wheel entry #{i} in config ({e}): {wheel!r}")
    return wheel_configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the airo-tulip server for a KELO Robile platform.")
    parser.add_argument("--config", required=True, help="Path to the robot YAML configuration file.")
    args = parser.parse_args()

    config = load_config(args.config)
    try:
        device = config["ethercat_device"]
        wheels = config["wheels"]
    except KeyError as e:
        raise ValueError(f"Config '{args.config}' is missing the required key: {e}")

    robot_configuration = RobotConfiguration(device, build_wheel_configs(wheels))
    server_kwargs = {key: config[key] for key in _OPTIONAL_SERVER_KEYS if config.get(key) is not None}

    logger.info(f"Starting airo-tulip server from config '{args.config}'.")
    TulipServer(robot_configuration, **server_kwargs).run()


if __name__ == "__main__":
    main()
