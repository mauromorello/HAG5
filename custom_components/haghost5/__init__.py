import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Set up the HAGhost5 integration."""
    _LOGGER.debug("Setting up HAGhost5 integration")
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass, config_entry):
    """Set up HAGhost5 from a config entry."""
    _LOGGER.debug("Setting up HAGhost5 entry")
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    return True

async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading HAGhost5 entry")
    hass.data[DOMAIN].pop(config_entry.entry_id)
    return True
