import logging
from homeassistant import config_entries, core

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up ETA Device from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Forward setup to platforms (e.g., sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload an ETA config entry."""
    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up stored data and option listener
        hass_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if hass_data:
            unsub = hass_data.get("unsub_options_update_listener")
            if unsub:
                unsub()
    else:
        _LOGGER.warning("Failed to unload ETA entry: %s", entry.entry_id)

    return unload_ok


async def options_update_listener(hass, config_entry):
    """Handle options update."""
    try:
        await hass.config_entries.async_reload(config_entry.entry_id)
    except config_entries.OperationNotAllowed:
        _LOGGER.warning(
            "ETA reload skipped — entry %s is in FAILED_UNLOAD state",
            config_entry.entry_id,
        )
