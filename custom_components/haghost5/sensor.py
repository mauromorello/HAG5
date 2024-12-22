import logging
from homeassistant.helpers.entity import Entity
from aiohttp import ClientSession, WSMsgType
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the WebSocket sensor."""
    _LOGGER.debug("async_setup_entry called for HAGhost5")
    ip_address = config_entry.data.get("ip_address")
    _LOGGER.debug("IP address from config: %s", ip_address)
    async_add_entities([WebSocketSensor(ip_address)], True)

class WebSocketSensor(Entity):
    """Representation of a WebSocket sensor."""

    def __init__(self, ip_address):
        """Initialize the sensor."""
        _LOGGER.debug("Initializing WebSocket sensor with IP: %s", ip_address)
        self._ip_address = ip_address
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return "WebSocket Sensor"

    @property
    def state(self):
        """Return the current state."""
        return self._state

    async def async_update(self):
        """Fetch new state data for the sensor."""
        ws_url = f"ws://{self._ip_address}:8081/"
        _LOGGER.debug("Connecting to WebSocket at: %s", ws_url)
        try:
            async with ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    msg = await ws.receive()
                    if msg.type == WSMsgType.TEXT:
                        self._state = msg.data
                        _LOGGER.debug("Received data: %s", msg.data)
                    elif msg.type == WSMsgType.ERROR:
                        _LOGGER.error("WebSocket error: %s", msg)
        except Exception as e:
            _LOGGER.error("Error connecting to WebSocket: %s", e)
