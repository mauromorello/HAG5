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
    sensors = [
        NozzleTemperatureRealSensor(ip_address),
        NozzleTemperatureSetpointSensor(ip_address),
    ]
    async_add_entities(sensors, update_before_add=True)
    hass.loop.create_task(sensors[0].listen_to_websocket(sensors))

class HAGhost5BaseSensor(SensorEntity):
    """Base class for HAGhost5 sensors."""

    def __init__(self, ip_address: str, sensor_name: str):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}
        self._sensor_name = sensor_name  # Name identifier for unique_id
        self._is_listening = False

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._ip_address}_{self._sensor_name}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": "HAGhost5 3D Printer",
            "manufacturer": "HAGhost5",
            "model": "3D Printer Sensors",
            "sw_version": "1.0",
        }

async def listen_to_websocket(self, sensors):
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
                            _LOGGER.debug("WebSocket message received: %s", msg.data)
                            for sensor in sensors:
                                await sensor.process_message(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            _LOGGER.error("WebSocket error: %s", msg)
                            break
        except Exception as e:
            _LOGGER.error("Error in WebSocket connection: %s", e)
            await asyncio.sleep(5)  # Wait before reconnecting


class NozzleTemperatureRealSensor(HAGhost5BaseSensor):
    """Sensor for the real nozzle temperature."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "nozzle_temperature_real")

    @property
    def name(self):
        return "Nozzle Temperature (Real)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "T:" in message:
            try:
                parts = message.split()
                for part in parts:
                    if part.startswith("T:"):
                        self._state = float(part.split(":")[1].split("/")[0])
                        _LOGGER.debug("Updated Nozzle Temperature (Real): %s", self._state)
                        self.async_write_ha_state()
            except (IndexError, ValueError) as e:
                _LOGGER.error("Error parsing nozzle real temperature: %s", e)


class NozzleTemperatureSetpointSensor(HAGhost5BaseSensor):
    """Sensor for the nozzle temperature setpoint."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "nozzle_temperature_setpoint")

    @property
    def name(self):
        return "Nozzle Temperature (Setpoint)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "T:" in message:
            try:
                parts = message.split()
                for part in parts:
                    if part.startswith("T:"):
                        self._state = float(part.split(":")[1].split("/")[1])
                        _LOGGER.debug("Updated Nozzle Temperature (Setpoint): %s", self._state)
                        self.async_write_ha_state()
            except (IndexError, ValueError) as e:
                _LOGGER.error("Error parsing nozzle setpoint temperature: %s", e)
