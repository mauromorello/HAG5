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
    nozzle_sensor = NozzleTemperatureSensor(ip_address)
    bed_sensor = BedTemperatureSensor(ip_address)
    async_add_entities([nozzle_sensor, bed_sensor], update_before_add=True)
    hass.loop.create_task(nozzle_sensor.listen_to_websocket(bed_sensor))

class HAGhost5BaseSensor(SensorEntity):
    """Base class for HAGhost5 sensors."""

    def __init__(self, ip_address: str):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}
        self._is_listening = False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def listen_to_websocket(self, other_sensor):
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
                                await self.process_message(msg.data, other_sensor)
                            elif msg.type == WSMsgType.ERROR:
                                _LOGGER.error("WebSocket error: %s", msg)
                                break
            except Exception as e:
                _LOGGER.error("Error in WebSocket connection: %s", e)
                await asyncio.sleep(5)  # Wait before reconnecting

    async def process_message(self, message: str, other_sensor):
        """Process incoming WebSocket messages."""
        _LOGGER.debug("Received data: %s", message)
        # Override in child classes to parse specific data
        pass

class NozzleTemperatureSensor(HAGhost5BaseSensor):
    """Sensor for the nozzle temperature."""

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Nozzle Temperature"

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"haghost5_nozzle_{self._ip_address.replace('.', '_')}"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:thermometer"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of this sensor."""
        return "°C"

    async def process_message(self, message: str, other_sensor):
        """Process the message for nozzle temperature."""
        try:
            if "T:" in message:
                parts = message.split()
                for part in parts:
                    if part.startswith("T:"):
                        self._state = float(part.split(":")[1].split("/")[0])
                        self.async_write_ha_state()
                    elif part.startswith("B:") and isinstance(other_sensor, BedTemperatureSensor):
                        other_sensor._state = float(part.split(":")[1].split("/")[0])
                        other_sensor.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Error parsing message: %s", e)

class BedTemperatureSensor(HAGhost5BaseSensor):
    """Sensor for the bed temperature."""

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Bed Temperature"

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return f"haghost5_bed_{self._ip_address.replace('.', '_')}"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:thermometer"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of this sensor."""
        return "°C"
