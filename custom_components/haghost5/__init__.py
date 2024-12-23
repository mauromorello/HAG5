import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration via YAML (not used)."""
    return True

async def async_setup_entry(hass, config_entry):
    """Set up the integration from a config entry."""
    _LOGGER.debug("Setting up HAGhost5 integration for IP: %s", config_entry.data["ip_address"])

    # Registra il dispositivo
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.data["ip_address"])},
        name=f"Printer ({config_entry.data['ip_address']})",
        manufacturer="HAGhost5",
        model="3D Printer"
    )

    # Avvia la piattaforma dei sensori
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    
    hass.config_entries.async_setup_platforms(entry, ["sensor"])


    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload the integration."""
    hass.data[DOMAIN].pop(entry.entry_id)
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True



