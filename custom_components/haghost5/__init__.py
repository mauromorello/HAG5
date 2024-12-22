import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HAGhost5 integration."""
    _LOGGER.debug("Setting up HAGhost5 integration")
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass, config_entry):
    """Set up HAGhost5 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading HAGhost5 entry")
    hass.data[DOMAIN].pop(config_entry.entry_id)

    # Unload the sensor platform
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")

    return True
