import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HAGhost5 integration."""
    _LOGGER.debug("Setting up HAGhost5 integration globally")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up HAGhost5 from a config entry."""
    _LOGGER.debug("Setting up HAGhost5 entry: %s", config_entry.entry_id)

    # Ensure domain data structure exists
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data

    # Forward setup to sensor platform
    try:
        _LOGGER.debug("Forwarding setup to sensor platform")
        await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
        _LOGGER.debug("Sensor platform setup forwarded successfully")
    except Exception as e:
        _LOGGER.error("Error forwarding setup to sensor platform: %s", e)
        return False

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading HAGhost5 entry: %s", config_entry.entry_id)

    # Remove entry from domain data
    if config_entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    # Unload the sensor platform
    try:
        _LOGGER.debug("Forwarding unload to sensor platform")
        unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        if unload_ok:
            _LOGGER.debug("Sensor platform unloaded successfully")
        else:
            _LOGGER.error("Failed to unload sensor platform")
    except Exception as e:
        _LOGGER.error("Error unloading sensor platform: %s", e)
        return False

    return True
