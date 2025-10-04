import logging
import asyncio

from homeassistant import config_entries, core

from .const import DOMAIN


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up ETA Device from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Forward the setup to the sensor platform (registers device via sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass, entry):
    """Unload an ETA config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    # Replace ["sensor"] with all the platforms you set up in async_setup_entry()
    if unload_ok:
        hass.data["eta"].pop(entry.entry_id)
    return unload_ok

async def options_update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
