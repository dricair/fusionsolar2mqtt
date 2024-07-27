# FusionSolar to MQTT

This scripts gets data from Huawei Fusion Solar using
[SmartPVMS 24.2.0 Northbound API](https://support.huawei.com/enterprise/en/doc/EDOC1100358266/306f6908/overview),
and publishes to MQTT.

It depends on [pyhfs](https://github.com/guillaumeblanc/pyhfs) python module interfacing
to SmartPVMS.

## Pre-requisite

To use the interface, you need to create API credentials on [Fusion Solar](https://uni005eu5.fusionsolar.huawei.com)
dashboard. The main requirement is to have **Administrator role** on the interface, as owner is not enough. If it's
not the case, ask your installator to make you administrator on the interface.

You need to create username and password as explained
[on the documentation](https://support.huawei.com/enterprise/en/doc/EDOC1100358266/fba05f66/obtaining-an-account).
The standard username and password would not work.

## Installation

Clone this repository and install the requirements:

- Optionally create a virtual environment:

      python3 -v venv venv
      source venv/bin/activate

- Install the requirements:

      pip3 install -r requirements.txt

- Copy `settings.yml.template` to `settings.yml` and fill the required fields, at least:

  - Username and password as explained above for Fusion Solar API access
  - Password for MQTT
  - You may adapt the remaining information

## Testing

### Fusion solar connection

Run the script once to test connection to FusionSolar and report the fields that are
reported. These fields could be used in a component listening to MQTT, for example
MQTT plugin in Jeedom.

    python3 ./fusionsolar2mqtt --list

Which outputs something like:

    fusionsolar:
      plants/Name/day_income                         : 0.0
      plants/Name/day_power                          : 34.8
      plants/Name/health_state                       : healthy
      plants/Name/health_state_id                    : 3
      ...
      devices/Name.INV-HV2330173288/active_power     : 0.0
      devices/Name.INV-HV2330173288/day_cap          : 34.85
      devices/Name.INV-HV2330173288/efficiency       : 100.0
      devices/Name.INV-HV2330173288/elec_freq        : 49.93
      devices/Name.INV-HV2330173288/inverter_state   : Grid-connected
      ...

While data reported to MQTT is hierarchy of dictionaries until topic
`fusionsolar`, encoded to JSON:

    {
      "plants": {
        "Name": {
          "day_income": 0.0,
          "day_power": 34.82,
          "health_state": "healthy",
          "health_state_id": 3,
          ...
        }
      },
      "devices": {
        "Name.INV-HV2330173288": {
          "active_power": 0.0,
          "day_cap": 34.85,
          "efficiency": 100.0,
          "elec_freq": 50.0,
          "inverter_state": "Grid-connected",
          ...
        }
      }
    }

### MQTT connection

Run the same script without `--list` to send data to the MQTT broker:

    python3 ./fusionsolar2mqtt




