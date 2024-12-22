import logging
import asyncio
from aiohttp import ClientSession, WSMsgType
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data.get("ip_address")
    sensor = HAGhost5Sensor(ip_address)
    async_add_entities([sensor], update_before_add=True)
    hass.loop.create_task(sensor.listen_to_websocket())

class HAGhost5Sensor(SensorEntity):
    """Representation of a HAGhost5 WebSocket sensor."""

    def __init__(self, ip_address: str):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}
        self._is_listening = False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"HAGhost5 WebSocket Sensor {self._ip_address}"

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"haghost5_{self._ip_address.replace('.', '_')}"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": "HAGhost5 WebSocket Device",
            "manufacturer": "HAGhost5",
            "model": "WebSocket Listener",
            "sw_version": "1.0",
            "entry_type": "service",
        }

    async def listen_to_websocket(self):
        """Maintain a persistent connection to the WebSocket."""
        ws_url = f"ws://{self._ip_address}:8081/"
        self._is_listening = True
        _LOGGER.debug("Connecting to WebSocket at: %s", ws_url)
        while self._is_listening:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        _LOGGER.info("Connected to WebSocket at: %s", ws_url)
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                await self.process_message(msg.data)
                            elif msg.type == WSMsgType.ERROR:
                                _LOGGER.error("WebSocket error: %s", msg)
                                break
            except Exception as e:
                _LOGGER.error("Error in WebSocket connection: %s", e)
                await asyncio.sleep(5)  # Wait before reconnecting

    async def process_message(self, message: str):
        """Process incoming WebSocket messages."""
        _LOGGER.debug("Received data: %s", message)
        # Update state and attributes based on the message
        self._state = message  # Example: set state to the raw message
        self._attributes["last_message"] = message
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Handle removal of the sensor."""
        _LOGGER.debug("Stopping WebSocket listener")
        self._is_listening = False
