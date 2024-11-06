from paho.mqtt import client as mqtt_client
import random
import datetime
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def mqtt_connect(mqtt_settings: Dict) -> mqtt_client.Client:
    """
    Connect to MQTT server and return client

    Args:
        mqtt_settings: dict of MQTT specific settings

    Returns:
        mqtt_client.Client: MQTT client
    """

    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            logger.debug("Connected to MQTT Broker!")
        else:
            logger.error("Failed to connect, return code %d\n", rc)

    client_id = f"fusionsolar-mqtt-{random.randint(0, 1000)}"
    client = mqtt_client.Client(
        client_id=client_id,
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
    )
    if mqtt_settings["auth"]:
        client.username_pw_set(mqtt_settings["username"], mqtt_settings["password"])
    client.on_connect = on_connect

    client.connect(
        mqtt_settings["host"], mqtt_settings["port"], mqtt_settings["reconnectPeriod"]
    )
    client.loop_start()
    logger.debug("MQTT connected")
    return client


def mqtt_publish(mqtt_settings: Dict, client: mqtt_client.Client, payload: Any):
    """
    Publish message (converted to JSON) to MQTT

    Args:
        client: MQTT client
        mqtt_settings: dict of MQTT specific settings
        msg: Message to send. If not string/int/float, it is converted to JSON string.
    """

    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    if isinstance(payload, (str, int, float)):
        msg = payload
    else:
        msg = json.dumps(payload, default=json_serial)

    logger.debug(f"Publishing message to topic {mqtt_settings['topic']}")
    result = client.publish(mqtt_settings["topic"], msg)
    result.wait_for_publish(mqtt_settings["connectTimeout"])
    if not result.is_published():
        logger.warning(f"Error on publishing the message: {result.rc}")
    else:
        logger.info("Message published")
