import pyhfs
from pathlib import Path
import logging
import json
import inspect
import datetime
from typing import Union, Dict

logger = logging.getLogger(__name__)


def get_devices(client: pyhfs.Client, device_file: Path) -> Dict[str, pyhfs.Plant]:
    """
    Get dictionary of plants and devices per plant:

    - Try to load from specified device file
    - If not available, load from Fusion Solar and save the file

    Args:
        client: pyhfs client, already connected.
    """
    plants = None
    if device_file.exists():
        logger.info(f"Reading list of devices from file {device_file}")
        logger.info("Remove this file if you want to refresh the list of devices")
        try:
            with device_file.open("r") as f:
                plants = pyhfs.Plant.from_list(json.load(f))
        except json.JSONDecodeError as e:
            logger.error(f"Unable to read file {device_file}: {e}")

    if plants is None:
        logger.info("Requesting list of devices.")
        plants = client.get_plant_list()
        client.get_device_list(plants)
        with device_file.open("w+") as f:
            data = [plant.data for plant in plants.values()]
            json.dump(data, f, indent=2)

    return plants


def data_to_dict(data: Union[pyhfs.PlantRealTimeData, pyhfs.DeviceRTData]) -> Dict:
    """
    Convert RealTime data class to a dictionary containing all the properties

    Args:
        data: PlantRealTimeData or DeviceRTData

    Returns:
        dict property name -> value
    """

    def isprop(x):
        return isinstance(x, property)

    def isexportable(x):
        return isinstance(x, (str, int, float, bool, datetime.datetime))

    # Note: properties can only be retrieved from the class, not the instance
    properties = [name for (name, _) in inspect.getmembers(data.__class__, isprop)]

    return {
        name: value
        for (name, value) in inspect.getmembers(data, isexportable)
        if name in properties
    }


def get_realtime_data(client: pyhfs.Client, plants: Dict[str, pyhfs.Plant]) -> Dict:
    """
    Get realtime data for plants and devices, with possible filtering

    Args:
        client: pyhfs client, already connected

    Returns:
        dict of PlantRealtimeData and DeviceRealtimeData organized as:
        {
            plants:
                plant_name: data
                plant_name: data
            devices:
                plant_name.device_name: data
                plant_name.device_name: data
        }
    """
    devices = {}
    for plant in plants.values():
        devices.update({d.id: d for d in plant.devices})

    plant_data = client.get_plant_realtime_data(plants)
    device_data = client.get_device_realtime_data(devices)

    def pname(data: pyhfs.PlantRealTimeData) -> str:
        return data.plant.name

    def dname(data: pyhfs.DeviceRTData) -> str:
        return f"{data.device.plant.name}.{data.device.name}"

    result = {}
    result["plants"] = {pname(pdata): data_to_dict(pdata) for pdata in plant_data}
    result["devices"] = {dname(ddata): data_to_dict(ddata) for ddata in device_data}
    return result
