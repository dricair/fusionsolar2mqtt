import pyhfs
from pathlib import Path
import logging
import json
import inspect
import datetime
from typing import Union, Dict

from pyhfs.api.devices import Device

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
        if x and isinstance(x, list):
            return isexportable(x[0])
        if x and isinstance(x, dict):
            return isexportable(list(x.values())[0])
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

    computed_data = compute_plant_data(plant_data, device_data)

    def pname(data: pyhfs.PlantRealTimeData) -> str:
        return data.plant.name

    def dname(data: pyhfs.DeviceRTData) -> str:
        return f"{data.device.plant.name}.{data.device.name}"

    result = {}
    result["plants"] = {pname(pdata): data_to_dict(pdata) for pdata in plant_data}
    for plant, value in computed_data.items():
        result["plants"][plant.name]["power"] = value["power"]
    result["devices"] = {dname(ddata): data_to_dict(ddata) for ddata in device_data}
    return result


def compute_plant_data(plant_data: list[pyhfs.PlantRealTimeData], device_data: list[pyhfs.DeviceRTData]) -> dict[pyhfs.Plant, dict[str,float]]:
    """
    Compute plant data corresponding to production, consumption and battery state,
    depending on what is available in the devices

    Args:
        plant_data (dict): real data for plants
        device_data (dict): real data for devices

    Returns:
        dict { plant: { name: value } }
    """
    # dict of plant -> plant data
    plants = {data.plant: data for data in plant_data}

    result = {}
    for plant in plants.keys():
        production, ch_battery, dis_battery, meter = None, None, None, None
        for ddata in [d for d in device_data if d.device.plant == plant]:
            if ddata.device.dev_data & Device.DEVICE_DATA_TYPES.PRODUCTION:
                # Production from PV. Unit: kW
                production = ddata.mppt_power * 1000
            if ddata.device.dev_data & Device.DEVICE_DATA_TYPES.BATTERY:
                # Battery charge / discharge. Positive if charging. Unit: kW
                ch_battery = max(ddata.ch_discharge_power, 0)
                dis_battery = max(-ddata.ch_discharge_power, 0)
            if ddata.device.dev_data & Device.DEVICE_DATA_TYPES.METER:
                # Negative if injecting power to grid. Unit: W
                meter = ddata.active_power

        if production is not None and meter is not None:
            consumption = production - meter - (ch_battery or 0) + (dis_battery or 0)
            result[plant] = {
                "power": {
                    "production": production,
                    "consumption": consumption,
                    "consumption_pv": min(production, consumption + (ch_battery or 0))
                }
            }

            if ch_battery is not None and dis_battery is not None:
                result[plant]["power"]["ch_battery"] = ch_battery
                result[plant]["power"]["dis_battery"] = dis_battery

    return result
