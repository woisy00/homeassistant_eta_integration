"""
Platform for ETA sensor integration in Home Assistant
"""

from __future__ import annotations

import logging
from datetime import timedelta

from voluptuous import Switch

from .api import EtaAPI, EtaAPIFactory, SensorDict

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

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_MODEL
from .const import DOMAIN, CHOOSEN_ENTITIES, FLOAT_DICT
from .api import SensorType, EtaSensorDesc

from homeassistant.helpers.device_registry import DeviceEntryType

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up ETA Device and sensors from config entry."""
    config = config_entry.data
    sensors = []

    # Device info for the ETA Device
    device_info = {
        "identifiers": {(DOMAIN, f"{config[CONF_HOST]}:{config[CONF_PORT]}")},
        "name": f"{config[CONF_NAME]}",
        "manufacturer": "ETA Heiztechnik GmbH",
        "model": f"{config[CONF_MODEL]}",
        #"entry_type": DeviceEntryType.SERVICE,
        "configuration_url": f"http://{config[CONF_HOST]}:{config[CONF_PORT]}/user/menu/"
    }

    # Create a single EtaAPI instance to share
    session = async_get_clientsession(hass)
    eta_api = EtaAPIFactory.get_instance(session, config[CONF_HOST], config[CONF_PORT])
    sensors_dict = await eta_api.get_sensors()

    # Add sensors for each selected entity
    for entity in config.get(CHOOSEN_ENTITIES, []):
        s = sensors_dict.byId(entity)
        sensors.append(
            EtaSensor(
                name=s.name,
                sensor=s,
                eta_api=eta_api,
                device_info=device_info,
                hass=hass
            )
        )

    async_add_entities(sensors, update_before_add=True)


class EtaSensor(SensorEntity):
    """Representation of an ETA Sensor."""

    def __init__(self, name, sensor: EtaSensorDesc, eta_api: EtaAPI, device_info, hass: HomeAssistant):
        self._attr_name = f"{device_info["name"]} {name}"
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, "eta_" + sensor.canonicalName().replace(" > ", "_"), hass=hass)
        self._sensor = sensor
        self._eta_api = eta_api
        self._device_info = device_info
        self._attr_unique_id = f"eta_{self._eta_api._host}_{self._eta_api._port}_{sensor.id}"
        self._value = None
        self._initialized = False

    @property
    def device_info(self):
        return self._device_info

    @property
    def native_value(self):
        return self._sensor.map(self._value)

    @property
    def extra_state_attributes(self):
        return {
            "sensor_id": self._sensor.id
        }    

    async def initialize(self):
        """Initialize sensor."""
        if not self._initialized:
            await self._eta_api.initializeSensor(self._sensor)
            self._attr_native_unit_of_measurement = self._sensor.unit
            self._attr_device_class = self.determine_device_class(self._sensor.unit)
            
            self._initialized = True
    
    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            await self.initialize()
            match self._sensor.sensor_type:
                case SensorType.TEXT:
                    value = await self._eta_api.get_data(self._sensor)
                    self._value = value
                case SensorType.NUMERIC:
                    value = await self._eta_api.get_data(self._sensor)
                    self._value = float(value)
        except Exception as e:
            _LOGGER.warning(f"Failed to update ETA sensor {self._attr_name}: {e}")

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
            "%rH": SensorDeviceClass.HUMIDITY
        }

        if unit in unit_dict_eta:
            return unit_dict_eta[unit]
        else:
            return None