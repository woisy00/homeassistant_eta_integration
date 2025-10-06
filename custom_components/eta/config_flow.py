"""
Config flow for ETA Device integration.
"""

import voluptuous as vol
from copy import deepcopy
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_MODEL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from .const import CHOOSEN_ENTITIES, DOMAIN, FLOAT_DICT
from .api import EtaAPI, EtaAPIFactory
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)


class EtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ETA Device."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Save host/port and move to sensor selection
            self._name = user_input[CONF_NAME]
            self._model = user_input[CONF_MODEL]
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            return await self.async_step_select_sensors()

        return await self._show_host_port_config(user_input)

    async def async_step_select_sensors(self, user_input=None):
        # Use instance variables set in async_step_user
        session = async_get_clientsession(self.hass)
        eta_api = EtaAPIFactory.get_instance(session, self._host, self._port)
        sensor_dict = await eta_api.get_sensors()

        if user_input is not None:
            # Save selected sensors (as URIs or labels as needed)
            selected_sensors = user_input[CHOOSEN_ENTITIES]
            #selected_sensors = [sensor_dict.byName(label).id for label in selected_labels]
            # Save config entry
            return self.async_create_entry(
                title=f"ETA Device ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_NAME: self._name,
                    CONF_MODEL: self._model,
                    CHOOSEN_ENTITIES: selected_sensors,
                },
            )

        return self.async_show_form(
            step_id="select_sensors",
            data_schema=vol.Schema(
                {
                    vol.Optional(CHOOSEN_ENTITIES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=sensor_dict.nameDict(),
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                }
            ),
            errors=self._errors,
        )

    async def _show_host_port_config(self, user_input=None):
        # Always return a form if no user_input
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="ETA Pellet Unit"): str,
                    vol.Required(CONF_MODEL, default=""): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=8080): int,
                }
            ),
            errors=self._errors,
        )

    # Add the options flow to the config flow
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EtaOptionsFlowHandler(config_entry)


class EtaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for ETA Device."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry  # ✅ store privately, not as .config_entry
        self._data = dict(config_entry.data)
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # Save host/port and move to sensor selection
        self._host = self._config_entry.data.get(CONF_HOST, "")
        self._port = self._config_entry.data.get(CONF_PORT, 8080)
        return await self.async_step_select_sensors()

    async def async_step_select_sensors(self, user_input=None):
        """Select sensors to configure."""
        session = async_get_clientsession(self.hass)
        eta_api = EtaAPIFactory.get_instance(session, self._host, self._port)
        sensor_dict = await eta_api.get_sensors()
        # Get current selection from options or fallback to data
        current = self._config_entry.options.get(
            CHOOSEN_ENTITIES,
            self._config_entry.data.get(CHOOSEN_ENTITIES, [])
        )
        
        if user_input is not None:
            entity_registry = async_get(self.hass)
            entries = async_entries_for_config_entry(entity_registry, self._config_entry.entry_id)
            entity_map = {e.unique_id.split("_")[3]: e for e in entries}
            
            removed_entities = [
                entity_map[entity_id]
                for entity_id in entity_map.keys()
                if entity_id not in user_input[CHOOSEN_ENTITIES]
            ]
            for e in removed_entities:
                # Unregister from HA
                await entity_registry.async_remove(e.entity_id)

            data = {CHOOSEN_ENTITIES: user_input[CHOOSEN_ENTITIES],                    
                    CONF_NAME: self._data[CONF_NAME],
                    CONF_MODEL: self._data[CONF_MODEL],
                    CONF_HOST: self._data[CONF_HOST],
                    CONF_PORT: self._data[CONF_PORT]}
                        
            return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="select_sensors",
            data_schema=vol.Schema(
                {
                    vol.Optional(CHOOSEN_ENTITIES, default=current): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=sensor_dict.nameDict(),                            
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                }
            ),
            errors=self._errors,
        )
        
    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self._config_entry.data.get(CONF_HOST), data=self.options
        )

