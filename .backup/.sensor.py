"""
Platform for ETA sensor integration in Home Assistant

Help Links:
 Entity Source: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py
 SensorEntity derives from Entity https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/__init__.py


author nigl

"""

from __future__ import annotations

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)
from .api import EtaAPI

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    ENTITY_ID_FORMAT,
)

from homeassistant.core import HomeAssistant
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN, CHOOSEN_ENTITIES, FLOAT_DICT

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up sensors dynamically based on the configuration."""
    config = config_entry.data

    sensors = []

    # Add selected entities
    for entity in config.get("selected_entities", []):
        sensors.append(
            EtaSensor(
                name=entity,
                uri=f"/path/to/{entity}",
                unit="unit",  # Replace with actual unit mapping
                config=config,
                hass=hass,
            )
        )

    # Add manually configured entities
    for manual_entity in config.get("manual_entities", []):
        sensors.append(
            EtaSensor(
                name=manual_entity["name"],
                uri=manual_entity["path"],
                unit="unit",  # Replace with actual unit mapping
                config=config,
                hass=hass,
            )
        )

    async_add_entities(sensors, update_before_add=True)


class EtaSensor(SensorEntity):
    """Representation of an ETA Sensor."""

    def __init__(self, name, uri, unit, config, hass):
        self._attr_name = name
        self.uri = uri
        self._attr_native_unit_of_measurement = unit
        self.host = config[CONF_HOST]
        self.port = config[CONF_PORT]
        self.session = async_get_clientsession(hass)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        eta_client = EtaAPI(self.session, self.host, self.port)
        value, _ = await eta_client.get_data(self.uri)
        self._attr_native_value = float(value)

    @staticmethod
    def determine_device_class(unit):
        unit_dict_eta = {
            "°C": SensorDeviceClass.TEMPERATURE,
            "W": SensorDeviceClass.POWER,
            "A": SensorDeviceClass.CURRENT,
            "Hz": SensorDeviceClass.FREQUENCY,
            "Pa": SensorDeviceClass.PRESSURE,
            "V": SensorDeviceClass.VOLTAGE,
            "W/m²": SensorDeviceClass.IRRADIANCE,
            "bar": SensorDeviceClass.PRESSURE,
            "kW": SensorDeviceClass.POWER,
            "kWh": SensorDeviceClass.ENERGY,
            "kg": SensorDeviceClass.WEIGHT,
            "mV": SensorDeviceClass.VOLTAGE,
            "s": SensorDeviceClass.DURATION,
            "%rH": SensorDeviceClass.HUMIDITY,
        }

        if unit in unit_dict_eta:
            return unit_dict_eta[unit]
        else:
            return None
