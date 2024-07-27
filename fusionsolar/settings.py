import yaml
from pathlib import Path
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def load_settings(filename: Path) -> Dict:
    """
    Load settings from Yaml file. Verify that correct keys are present.

    Args:
        filename: file to load (Yaml format)

    Returns:
        dict of loaded file
    """
    with filename.open("r") as f:
        data = yaml.load(f, yaml.Loader)

    schema = {
        "system": ("logLevel",),
        "fusionsolar": ("username", "password"),
        "mqtt": (
            "auth",
            "connectTimeout",
            "host",
            "password",
            "port",
            "reconnectPeriod",
            "topic",
            "username",
        ),
    }

    for key, values in schema.items():
        if key not in data:
            logger.fatal(f"Expecting key {key} at root in file {filename}")
            exit(-1)
        for subkey in values:
            if subkey not in data[key]:
                logger.fatal(
                    f"Expecting sub-key {subkey} inside key {key} in file {filename}"
                )
                exit(-1)

    return data
