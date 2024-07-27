#!/usr/bin/env python3

from pathlib import Path
import argparse
import pyhfs
import logging
from typing import Dict, List, Tuple

from fusionsolar.settings import load_settings
from fusionsolar.mqtt import mqtt_connect, mqtt_publish
from fusionsolar.fusionsolar import get_devices, get_realtime_data

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def format_data(data: Dict) -> str:
    """
    Format data for --list
    """

    def to_list(data: Dict) -> List[str]:
        result = []
        for key, value in data.items():
            if isinstance(value, dict):
                for k, v in to_list(value):
                    result.append((f"{key}/{k}", v))
            else:
                result.append((key, value))

        return result

    list_data = to_list(data)
    max_length = max([len(d[0]) for d in list_data])
    return "  " + "\n  ".join([f"{k:{max_length}}: {v}" for k, v in list_data])


def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Define argument parser and parse arguments

    Returns:
       (parser, args): parser and parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Request data from Fusion Solar and publish as MQTT"
    )

    parser.add_argument(
        "--settings",
        type=Path,
        default=Path("settings.yml"),
        help="Settings file in Yaml format",
    )
    parser.add_argument(
        "--device-file",
        type=Path,
        default=Path("devices.json", help="Devices retrieved from Fusion Solar"),
    )
    parser.add_argument(
        "--list", action="store_true", help="List Plant/Devices commands and exit"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug messages")

    args = parser.parse_args()

    if not args.settings.exists():
        parser.error(f"Settings file {args.settings} does not exist")

    return parser, args


if __name__ == "__main__":
    conf_file = Path("settings.yml")
    settings = load_settings(conf_file)
    parser, args = parse_args()

    sys_settings = settings["system"]
    fs_settings = settings["fusionsolar"]
    mqtt_settings = settings["mqtt"]

    if sys_settings["logLevel"] not in LOG_LEVELS:
        parser.error(
            f"Level {sys_settings['logLevel']} not supported: {', '.join(LOG_LEVELS.keys())}"
        )
    level = logging.DEBUG if args.debug else LOG_LEVELS[sys_settings["logLevel"]]

    logging.basicConfig(
        format="%(module)-20s %(levelname)-8s: %(message)s", level=level
    )
    logger = logging.getLogger(__name__)

    # Get information from Fusion Solar
    with pyhfs.ClientSession(
        user=fs_settings["username"], password=fs_settings["password"]
    ) as client:
        plants = get_devices(client, args.device_file)
        data = get_realtime_data(client, plants)

    if args.list:
        logger.info("\nList of variables reported to MQTT:\n")
        print(f"{mqtt_settings['topic']}:")
        print(format_data(data))
        exit(0)

    client = mqtt_connect(settings["mqtt"])
    mqtt_publish(settings["mqtt"], client, data)
    client.disconnect()
